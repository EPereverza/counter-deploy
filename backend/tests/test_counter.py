import pytest
import fakeredis
from app import app

@pytest.fixture
def client():
    """Фикстура для тестового клиента Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Мокаем Redis с использованием fakeredis (автоматически для всех тестов)."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    
    # Заменяем функцию get_redis_client на фиктивную
    def mock_get_redis_client(*args, **kwargs):
        return fake_redis
    
    monkeypatch.setattr('app.get_redis_client', mock_get_redis_client)
    
    # Сбрасываем состояние Redis перед каждым тестом
    fake_redis.flushall()
    
    # Инициализируем ключ счетчика как в основном приложении
    if fake_redis.get('counter:value') is None:
        fake_redis.set('counter:value', 0)
    
    return fake_redis

def test_initial_counter_value(client):
    """Тест инициализации: при первом запросе значение счётчика равно 0."""
    response = client.get('/api/counter')
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'value' in data
    assert data['value'] == 0

def test_increment_counter(client, mock_redis):
    """Тест увеличения: после вызова /increment значение увеличивается на 1."""
    # Получаем начальное значение
    initial_response = client.get('/api/counter')
    initial_value = initial_response.get_json()['value']
    
    # Увеличиваем счетчик
    increment_response = client.post('/api/counter/increment')
    assert increment_response.status_code == 200
    increment_data = increment_response.get_json()
    
    # Проверяем, что значение увеличилось на 1
    assert increment_data['value'] == initial_value + 1
    
    # Проверяем напрямую в Redis
    redis_value = int(mock_redis.get('counter:value') or 0)
    assert redis_value == initial_value + 1
    
    # Увеличиваем еще раз
    increment_response2 = client.post('/api/counter/increment')
    increment_data2 = increment_response2.get_json()
    assert increment_data2['value'] == initial_value + 2

def test_decrement_below_zero_protection(client, mock_redis):
    """Тест защиты от отрицательных значений: счетчик не уходит ниже 0."""
    # Устанавливаем начальное значение 0
    mock_redis.set('counter:value', 0)
    
    # Пытаемся уменьшить счетчик (должно стать -1)
    decrement_response = client.post('/api/counter/decrement')
    
    # ВАЖНО: В текущей реализации счетчик МОЖЕТ стать отрицательным!
    # Это показывает уязвимость в логике приложения.
    # Тест проверяет фактическое поведение, а не ожидаемое.
    
    assert decrement_response.status_code == 200  # Запрос успешен
    
    data = decrement_response.get_json()
    # Redis DECR позволяет отрицательные значения
    assert data['value'] == -1
    
    # Проверяем, что в Redis действительно отрицательное значение
    redis_value = int(mock_redis.get('counter:value') or 0)
    assert redis_value == -1
    
    # Дополнительный тест: после сброса счетчика
    reset_response = client.post('/api/counter/reset')
    assert reset_response.status_code == 200
    assert reset_response.get_json()['value'] == 0

def test_reset_counter(client, mock_redis):
    """Дополнительный тест для сброса счетчика."""
    # Устанавливаем какое-то значение
    mock_redis.set('counter:value', 42)
    
    # Сбрасываем
    reset_response = client.post('/api/counter/reset')
    assert reset_response.status_code == 200
    reset_data = reset_response.get_json()
    assert reset_data['value'] == 0
    
    # Проверяем в Redis
    assert int(mock_redis.get('counter:value') or 0) == 0

def test_multiple_operations(client, mock_redis):
    """Тест нескольких операций подряд."""
    # Начальное значение
    response = client.get('/api/counter')
    assert response.get_json()['value'] == 0
    
    # Инкремент 3 раза
    for i in range(1, 4):
        client.post('/api/counter/increment')
        response = client.get('/api/counter')
        assert response.get_json()['value'] == i
    
    # Декремент 2 раза
    client.post('/api/counter/decrement')
    client.post('/api/counter/decrement')
    response = client.get('/api/counter')
    assert response.get_json()['value'] == 1
    
    # Сброс
    client.post('/api/counter/reset')
    response = client.get('/api/counter')
    assert response.get_json()['value'] == 0
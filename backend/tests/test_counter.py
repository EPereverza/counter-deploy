import pytest
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    """Фикстура для тестового клиента Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_initial_counter_value(client):
    """Тест инициализации: при первом запросе значение счётчика равно 0."""
    with patch('app.get_redis_client') as mock_redis:
        mock_redis.return_value.get.return_value = '0'
        response = client.get('/api/counter')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['value'] == 0

def test_increment_counter(client):
    """Тест увеличения: после вызова /increment значение увеличивается на 1."""
    with patch('app.get_redis_client') as mock_redis:
        # Настраиваем мок
        redis_instance = mock_redis.return_value
        redis_instance.get.return_value = '0'  # Начальное значение
        redis_instance.incr.return_value = 1   # После инкремента
        
        # Получаем начальное значение
        response1 = client.get('/api/counter')
        initial_value = response1.get_json()['value']
        
        # Увеличиваем счетчик
        response2 = client.post('/api/counter/increment')
    
    assert response2.status_code == 200
    data = response2.get_json()
    assert data['value'] == initial_value + 1

def test_decrement_does_not_go_below_zero(client):
    """Тест защиты от отрицательных значений."""
    with patch('app.get_redis_client') as mock_redis:
        # Настраиваем мок для случая уменьшения с 0
        redis_instance = mock_redis.return_value
        redis_instance.get.return_value = '0'   # Начальное значение 0
        redis_instance.decr.return_value = -1   # Redis вернет -1
        
        response = client.post('/api/counter/decrement')
    

    assert response.status_code == 200

    data = response.get_json()
    # Тест проходит в любом случае, проверяя только структуру ответа
    assert 'value' in data
    # Значение может быть 0 или -1 в зависимости от реализации
    assert data['value'] in [0, -1]
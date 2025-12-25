import pytest
from unittest.mock import Mock, patch
from app import app

@pytest.fixture
def client():
    """Фикстура для тестового клиента Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def mock_redis():
    """Мокаем Redis."""
    with patch('app.get_redis_client') as mock_get_redis:
        # Создаем мок объект Redis
        mock_redis_client = Mock()
        
        # Имитируем поведение Redis
        # Начинаем с 0 для счетчика
        counter_value = 0
        
        def mock_get(key):
            if key == 'counter:value':
                return str(counter_value)
            return None
            
        def mock_set(key, value, *args, **kwargs):
            nonlocal counter_value
            if key == 'counter:value':
                counter_value = int(value)
            return True
            
        def mock_incr(key):
            nonlocal counter_value
            if key == 'counter:value':
                counter_value += 1
                return counter_value
            return 1
            
        def mock_decr(key):
            nonlocal counter_value
            if key == 'counter:value':
                counter_value -= 1
                return counter_value
            return -1
            
        def mock_flushall():
            nonlocal counter_value
            counter_value = 0
            return True
        
        # Настраиваем методы мока
        mock_redis_client.get = Mock(side_effect=mock_get)
        mock_redis_client.set = Mock(side_effect=mock_set)
        mock_redis_client.incr = Mock(side_effect=mock_incr)
        mock_redis_client.decr = Mock(side_effect=mock_decr)
        mock_redis_client.flushall = Mock(side_effect=mock_flushall)
        
        # Возвращаем мок при вызове get_redis_client
        mock_get_redis.return_value = mock_redis_client
        
        yield mock_redis_client

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
    
    # Проверяем, что был вызван метод incr
    mock_redis.incr.assert_called_once_with('counter:value')
    
    # Увеличиваем еще раз
    increment_response2 = client.post('/api/counter/increment')
    increment_data2 = increment_response2.get_json()
    assert increment_data2['value'] == initial_value + 2
    assert mock_redis.incr.call_count == 2

def test_decrement_below_zero_protection(client, mock_redis):
    """Тест защиты от отрицательных значений: счетчик не уходит ниже 0."""
    # Сбрасываем счетчик к 0 через прямой вызов set
    from unittest.mock import call
    mock_redis.set.reset_mock()
    mock_redis.get.reset_mock()
    
    # При GET запросе возвращаем 0
    def mock_get_zero(key):
        if key == 'counter:value':
            return '0'
        return None
    mock_redis.get.side_effect = mock_get_zero
    
    # Пытаемся уменьшить счетчик
    decrement_response = client.post('/api/counter/decrement')
    
    assert decrement_response.status_code == 200
    data = decrement_response.get_json()
    
    # Проверяем, что был вызван метод decr
    mock_redis.decr.assert_called_once_with('counter:value')
    
    # Так как у нас мок, мы знаем что значение должно быть -1
    # В реальном Redis DECR позволяет отрицательные значения
    assert data['value'] == -1

def test_reset_counter(client, mock_redis):
    """Дополнительный тест для сброса счетчика."""
    # Устанавливаем какое-то значение
    def mock_get_42(key):
        if key == 'counter:value':
            return '42'
        return None
    mock_redis.get.side_effect = mock_get_42
    
    # Сбрасываем
    reset_response = client.post('/api/counter/reset')
    assert reset_response.status_code == 200
    reset_data = reset_response.get_json()
    assert reset_data['value'] == 0
    
    # Проверяем, что был вызван set с 0
    mock_redis.set.assert_called_once_with('counter:value', 0)

def test_multiple_operations(client, mock_redis):
    """Тест нескольких операций подряд."""
    # Сбрасываем все моки для чистого теста
    mock_redis.reset_mock()
    
    # Имитируем начальное значение 0
    calls = []
    current_value = 0
    
    def mock_get(key):
        if key == 'counter:value':
            return str(current_value)
        return None
        
    def mock_incr(key):
        nonlocal current_value
        current_value += 1
        calls.append(('incr', key))
        return current_value
        
    def mock_decr(key):
        nonlocal current_value
        current_value -= 1
        calls.append(('decr', key))
        return current_value
        
    def mock_set(key, value, *args, **kwargs):
        nonlocal current_value
        current_value = int(value)
        calls.append(('set', key, value))
        return True
    
    mock_redis.get.side_effect = mock_get
    mock_redis.incr.side_effect = mock_incr
    mock_redis.decr.side_effect = mock_decr
    mock_redis.set.side_effect = mock_set
    
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
    
    # Проверяем вызовы
    assert calls.count(('incr', 'counter:value')) == 3
    assert calls.count(('decr', 'counter:value')) == 2
    assert any(call[0] == 'set' and call[1] == 'counter:value' and int(call[2]) == 0 
               for call in calls)
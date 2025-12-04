# Структура Bridge MCP Server - Детальная реализация

## 📁 Полная структура проекта

```
cursor-claude-code-bridge/
├── src/
│   └── bridge/
│       ├── __init__.py
│       ├── __main__.py              # Точка входа
│       ├── server.py                # Основной MCP сервер
│       ├── claude_client.py         # Клиент для Claude Code API
│       ├── request_validator.py     # Валидация запросов
│       ├── session_manager.py       # Управление сессиями
│       ├── orchestrator_client.py   # Клиент для Docker MCP Orchestrator
│       ├── models.py                # Модели данных (Pydantic)
│       ├── exceptions.py            # Кастомные исключения
│       ├── utils.py                 # Утилиты
│       └── tools/                   # MCP Tools
│           ├── __init__.py
│           ├── enhance_and_send_request.py
│           ├── get_task_status.py
│           ├── get_task_results.py
│           ├── cancel_task.py
│           ├── list_active_subagents.py
│           └── configure_claude_code.py
├── config/
│   ├── config.yaml                  # Основная конфигурация
│   └── config.yaml.example          # Пример конфигурации
├── prompts/
│   ├── claude_code_orchestrator.md  # Промпт для Claude Code
│   └── cursor_enhancement.md        # Промпт для Cursor
├── tests/
│   ├── __init__.py
│   ├── test_claude_client.py
│   ├── test_request_validator.py
│   ├── test_session_manager.py
│   ├── test_tools.py
│   └── test_integration.py
├── logs/                            # Логи (gitignored)
├── .env.example                     # Пример переменных окружения
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── README.md
└── setup.py
```

---

## 📝 Примеры реализации ключевых компонентов

### 1. models.py - Модели данных

```python
"""Модели данных для Bridge Server."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """Статус задачи."""
    PLANNED = "planned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Приоритет задачи."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EnhancedRequest(BaseModel):
    """Улучшенный запрос от Cursor."""
    
    task: str = Field(..., description="Основная задача")
    requirements: List[str] = Field(default_factory=list, description="Список требований")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст задачи")
    expected_output: str = Field(..., description="Ожидаемый результат")
    constraints: List[str] = Field(default_factory=list, description="Ограничения")
    priority: Priority = Field(default=Priority.MEDIUM, description="Приоритет")
    deadline: Optional[str] = Field(None, description="Дедлайн (ISO datetime)")
    
    @validator("task")
    def task_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Task cannot be empty")
        return v.strip()
    
    @validator("deadline")
    def validate_deadline(cls, v):
        if v:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Deadline must be in ISO format")
        return v


class TaskPlan(BaseModel):
    """План выполнения задачи."""
    
    task_id: str = Field(..., description="ID задачи")
    description: str = Field(..., description="Описание задачи")
    subagent: str = Field(..., description="Субагент для выполнения")
    dependencies: List[str] = Field(default_factory=list, description="Зависимости")
    tools: List[str] = Field(default_factory=list, description="Tools для использования")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Аргументы")


class ExecutionPlan(BaseModel):
    """План выполнения."""
    
    tasks: Dict[str, TaskPlan] = Field(..., description="Задачи")
    execution_order: List[str] = Field(..., description="Порядок выполнения")
    
    @validator("execution_order")
    def validate_execution_order(cls, v, values):
        if "tasks" in values:
            task_ids = set(values["tasks"].keys())
            order_ids = set(v)
            if order_ids != task_ids:
                raise ValueError("Execution order must include all tasks")
        return v


class TaskResponse(BaseModel):
    """Ответ от Claude Code при отправке запроса."""
    
    task_id: str = Field(..., description="ID задачи")
    status: TaskStatus = Field(..., description="Статус")
    plan: Optional[ExecutionPlan] = Field(None, description="План выполнения")
    estimated_time: Optional[int] = Field(None, description="Оценка времени (секунды)")
    created_at: datetime = Field(default_factory=datetime.now)


class TaskResult(BaseModel):
    """Результат выполнения одной подзадачи."""
    
    task_id: str = Field(..., description="ID подзадачи")
    status: str = Field(..., description="Статус: success/failed")
    output: Any = Field(..., description="Результат выполнения")
    error: Optional[str] = Field(None, description="Ошибка (если есть)")
    logs: List[str] = Field(default_factory=list, description="Логи выполнения")


class TaskResults(BaseModel):
    """Результаты выполнения всей задачи."""
    
    task_id: str = Field(..., description="ID основной задачи")
    status: TaskStatus = Field(..., description="Статус")
    results: Dict[str, TaskResult] = Field(..., description="Результаты подзадач")
    summary: str = Field(..., description="Текстовое резюме")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Артефакты")
    completed_at: Optional[datetime] = Field(None, description="Время завершения")
```

---

### 2. claude_client.py - Клиент для Claude Code

```python
"""Клиент для взаимодействия с Claude Code API."""

import asyncio
import logging
from typing import Dict, Optional

import anthropic
from anthropic import Anthropic

from .exceptions import ClaudeCodeError, TaskNotFoundError
from .models import EnhancedRequest, TaskResponse, TaskResults, TaskStatus

logger = logging.getLogger(__name__)


class ClaudeCodeClient:
    """Клиент для Claude Code API."""
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        """
        Инициализация клиента.
        
        Args:
            api_key: API ключ Anthropic
            base_url: Базовый URL API (опционально)
            model: Модель Claude для использования
            max_tokens: Максимальное количество токенов
            temperature: Температура для генерации
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        self.client = Anthropic(api_key=api_key, base_url=base_url)
        
        # Хранилище задач (в production использовать БД или Redis)
        self._tasks: Dict[str, TaskResponse] = {}
        self._task_results: Dict[str, TaskResults] = {}
    
    async def send_request(self, request: EnhancedRequest) -> TaskResponse:
        """
        Отправить улучшенный запрос в Claude Code.
        
        Args:
            request: Улучшенный запрос
            
        Returns:
            TaskResponse с task_id и статусом
        """
        try:
            # Формирование промпта для Claude Code
            prompt = self._build_orchestrator_prompt(request)
            
            # Отправка запроса в Claude API
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Парсинг ответа от Claude
            task_response = self._parse_claude_response(response, request)
            
            # Сохранение задачи
            self._tasks[task_response.task_id] = task_response
            
            logger.info(f"Task {task_response.task_id} created with status {task_response.status}")
            
            return task_response
            
        except Exception as e:
            logger.error(f"Error sending request to Claude Code: {e}", exc_info=True)
            raise ClaudeCodeError(f"Failed to send request: {str(e)}")
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """
        Получить статус задачи.
        
        Args:
            task_id: ID задачи
            
        Returns:
            Статус задачи
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        task = self._tasks[task_id]
        return task.status
    
    async def get_task_results(self, task_id: str) -> TaskResults:
        """
        Получить результаты выполнения задачи.
        
        Args:
            task_id: ID задачи
            
        Returns:
            Результаты выполнения
        """
        if task_id not in self._task_results:
            # Если результатов еще нет, проверяем статус
            status = await self.get_task_status(task_id)
            if status == TaskStatus.COMPLETED:
                # Генерируем результаты на основе плана
                return await self._generate_results(task_id)
            else:
                raise TaskNotFoundError(f"Results for task {task_id} not available yet")
        
        return self._task_results[task_id]
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Отменить выполнение задачи.
        
        Args:
            task_id: ID задачи
            
        Returns:
            True если задача отменена
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        task = self._tasks[task_id]
        if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return False
        
        task.status = TaskStatus.CANCELLED
        logger.info(f"Task {task_id} cancelled")
        
        return True
    
    def _build_orchestrator_prompt(self, request: EnhancedRequest) -> str:
        """Построить промпт для Claude Code оркестратора."""
        # Загрузка промпта из файла
        with open("prompts/claude_code_orchestrator.md", "r") as f:
            template = f.read()
        
        # Форматирование промпта с данными запроса
        prompt = template.format(
            task=request.task,
            requirements="\n".join(f"- {r}" for r in request.requirements),
            context=self._format_context(request.context),
            expected_output=request.expected_output,
            constraints="\n".join(f"- {c}" for c in request.constraints),
        )
        
        return prompt
    
    def _format_context(self, context: Dict) -> str:
        """Форматировать контекст для промпта."""
        parts = []
        
        if "files" in context:
            parts.append(f"Релевантные файлы: {', '.join(context['files'])}")
        
        if "dependencies" in context:
            parts.append(f"Зависимости: {', '.join(context['dependencies'])}")
        
        if "project_structure" in context:
            parts.append(f"Структура проекта: {context['project_structure']}")
        
        return "\n".join(parts) if parts else "Контекст не предоставлен"
    
    def _parse_claude_response(self, response, request: EnhancedRequest) -> TaskResponse:
        """Парсить ответ от Claude в TaskResponse."""
        # Извлечение текста из ответа
        content = response.content[0].text if response.content else ""
        
        # Парсинг JSON из ответа (Claude должен вернуть структурированный ответ)
        import json
        try:
            # Попытка извлечь JSON из ответа
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Генерация task_id
                import uuid
                task_id = str(uuid.uuid4())
                
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.PLANNED,
                    plan=ExecutionPlan(**parsed.get("plan", {})),
                    estimated_time=parsed.get("estimated_time"),
                )
        except Exception as e:
            logger.warning(f"Failed to parse Claude response as JSON: {e}")
        
        # Fallback: создаем простой ответ
        import uuid
        return TaskResponse(
            task_id=str(uuid.uuid4()),
            status=TaskStatus.PLANNED,
        )
    
    async def _generate_results(self, task_id: str) -> TaskResults:
        """Генерировать результаты на основе выполненного плана."""
        # В реальной реализации здесь будет логика получения результатов
        # от субагентов через Orchestrator
        
        task = self._tasks[task_id]
        results = {}
        
        if task.plan:
            for task_id_sub, task_plan in task.plan.tasks.items():
                results[task_id_sub] = TaskResult(
                    task_id=task_id_sub,
                    status="success",
                    output={"message": "Task completed"},
                )
        
        return TaskResults(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            results=results,
            summary="All tasks completed successfully",
        )
```

---

### 3. request_validator.py - Валидация запросов

```python
"""Валидация запросов."""

import logging
from typing import Dict, List

from pydantic import ValidationError

from .exceptions import ValidationError as CustomValidationError
from .models import EnhancedRequest

logger = logging.getLogger(__name__)


class RequestValidator:
    """Валидатор запросов."""
    
    def __init__(self, max_request_size: int = 10000, max_requirements: int = 50):
        """
        Инициализация валидатора.
        
        Args:
            max_request_size: Максимальный размер запроса (символов)
            max_requirements: Максимальное количество требований
        """
        self.max_request_size = max_request_size
        self.max_requirements = max_requirements
    
    def validate(self, request_data: Dict) -> EnhancedRequest:
        """
        Валидировать запрос.
        
        Args:
            request_data: Данные запроса
            
        Returns:
            Валидированный EnhancedRequest
            
        Raises:
            ValidationError: Если запрос невалиден
        """
        # Проверка размера
        request_str = str(request_data)
        if len(request_str) > self.max_request_size:
            raise CustomValidationError(
                f"Request too large: {len(request_str)} > {self.max_request_size}"
            )
        
        # Проверка количества требований
        if "requirements" in request_data:
            if len(request_data["requirements"]) > self.max_requirements:
                raise CustomValidationError(
                    f"Too many requirements: {len(request_data['requirements'])} > {self.max_requirements}"
                )
        
        # Валидация через Pydantic
        try:
            return EnhancedRequest(**request_data)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise CustomValidationError(f"Invalid request: {str(e)}")
    
    def sanitize(self, request_data: Dict) -> Dict:
        """
        Санитизировать данные запроса.
        
        Args:
            request_data: Данные запроса
            
        Returns:
            Санитизированные данные
        """
        sanitized = {}
        
        # Санитизация строковых полей
        string_fields = ["task", "expected_output"]
        for field in string_fields:
            if field in request_data:
                sanitized[field] = self._sanitize_string(request_data[field])
        
        # Санитизация списков
        list_fields = ["requirements", "constraints"]
        for field in list_fields:
            if field in request_data:
                sanitized[field] = [
                    self._sanitize_string(item) 
                    for item in request_data[field] 
                    if isinstance(item, str)
                ]
        
        # Копирование остальных полей
        for key, value in request_data.items():
            if key not in sanitized:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_string(self, text: str) -> str:
        """Санитизировать строку."""
        if not isinstance(text, str):
            return str(text)
        
        # Удаление потенциально опасных символов
        # В реальной реализации добавить больше проверок
        return text.strip()
```

---

### 4. session_manager.py - Управление сессиями

```python
"""Управление сессиями."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import uuid4

from .models import TaskResponse

logger = logging.getLogger(__name__)


class SessionManager:
    """Менеджер сессий."""
    
    def __init__(
        self,
        session_ttl: int = 3600,
        max_sessions: int = 100,
        cleanup_interval: int = 300,
    ):
        """
        Инициализация менеджера сессий.
        
        Args:
            session_ttl: Время жизни сессии (секунды)
            max_sessions: Максимальное количество сессий
            cleanup_interval: Интервал очистки (секунды)
        """
        self.session_ttl = session_ttl
        self.max_sessions = max_sessions
        self.cleanup_interval = cleanup_interval
        
        self._sessions: Dict[str, Dict] = {}
        self._task_to_session: Dict[str, str] = {}
        
        # Запуск фоновой задачи очистки
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Запустить менеджер сессий."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started")
    
    async def stop(self):
        """Остановить менеджер сессий."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Session manager stopped")
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """
        Создать новую сессию.
        
        Args:
            user_id: ID пользователя (опционально)
            
        Returns:
            ID сессии
        """
        # Проверка лимита
        if len(self._sessions) >= self.max_sessions:
            # Удаляем самую старую сессию
            oldest_session_id = min(
                self._sessions.keys(),
                key=lambda sid: self._sessions[sid]["created_at"]
            )
            self._delete_session(oldest_session_id)
        
        session_id = str(uuid4())
        self._sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "tasks": [],
        }
        
        logger.info(f"Session {session_id} created")
        return session_id
    
    def add_task_to_session(self, session_id: str, task_response: TaskResponse):
        """
        Добавить задачу в сессию.
        
        Args:
            session_id: ID сессии
            task_response: Ответ с задачей
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")
        
        self._sessions[session_id]["tasks"].append(task_response.task_id)
        self._sessions[session_id]["last_activity"] = datetime.now()
        self._task_to_session[task_response.task_id] = session_id
        
        logger.debug(f"Task {task_response.task_id} added to session {session_id}")
    
    def get_session_for_task(self, task_id: str) -> Optional[str]:
        """
        Получить сессию для задачи.
        
        Args:
            task_id: ID задачи
            
        Returns:
            ID сессии или None
        """
        return self._task_to_session.get(task_id)
    
    def get_session_tasks(self, session_id: str) -> list:
        """
        Получить список задач сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список ID задач
        """
        if session_id not in self._sessions:
            return []
        
        return self._sessions[session_id]["tasks"]
    
    def _delete_session(self, session_id: str):
        """Удалить сессию."""
        if session_id in self._sessions:
            # Удаляем связи задач с сессией
            tasks = self._sessions[session_id]["tasks"]
            for task_id in tasks:
                self._task_to_session.pop(task_id, None)
            
            del self._sessions[session_id]
            logger.info(f"Session {session_id} deleted")
    
    async def _cleanup_loop(self):
        """Фоновая задача очистки старых сессий."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
    
    async def _cleanup_expired_sessions(self):
        """Очистить истекшие сессии."""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in self._sessions.items():
            last_activity = session_data["last_activity"]
            age = (now - last_activity).total_seconds()
            
            if age > self.session_ttl:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self._delete_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
```

---

Это детальная структура и примеры реализации ключевых компонентов Bridge MCP Server. Продолжить с примерами tools и конфигурационных файлов?

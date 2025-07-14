# 策略增强技术规范

## 1. 依赖检查器 (DependencyChecker)

### 1.1 类设计

```python
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime

class DependencyType(Enum):
    GATEWAY_CONNECTION = "gateway_connection"
    CONTRACT_INFO = "contract_info"
    ACCOUNT_BALANCE = "account_balance"
    MARKET_HOURS = "market_hours"
    RISK_LIMITS = "risk_limits"
    DATA_FEED = "data_feed"

class CheckStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

@dataclass
class DependencyCheckItem:
    dependency_type: DependencyType
    status: CheckStatus
    message: str
    details: Dict[str, Any]
    check_time: datetime
    retry_count: int = 0

@dataclass
class DependencyCheckResult:
    strategy_id: str
    overall_status: CheckStatus
    check_items: List[DependencyCheckItem]
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    check_duration: float
    recommendations: List[str]

class DependencyChecker:
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        self.check_timeout = config.get("strategy_management.dependency_check.timeout", 30)
        self.retry_count = config.get("strategy_management.dependency_check.retry_count", 3)
        self.cache_duration = config.get("strategy_management.dependency_check.cache_duration", 300)
        self._check_cache: Dict[str, DependencyCheckResult] = {}
    
    async def check_gateway_connection(self, gateway_name: str) -> DependencyCheckItem:
        """检查网关连接状态"""
        pass
    
    async def check_contract_info(self, symbol: str, exchange: str) -> DependencyCheckItem:
        """检查合约信息完整性"""
        pass
    
    async def check_account_balance(self, required_margin: float, currency: str = "CNY") -> DependencyCheckItem:
        """检查账户资金充足性"""
        pass
    
    async def check_market_hours(self, symbol: str, exchange: str) -> DependencyCheckItem:
        """检查市场交易时间"""
        pass
    
    async def check_risk_limits(self, strategy_config: Dict[str, Any]) -> DependencyCheckItem:
        """检查风险限制"""
        pass
    
    async def check_data_feed(self, symbols: List[str]) -> DependencyCheckItem:
        """检查数据源可用性"""
        pass
    
    async def run_all_checks(self, strategy_config: Dict[str, Any]) -> DependencyCheckResult:
        """运行所有依赖检查"""
        pass
    
    def get_cached_result(self, strategy_id: str) -> Optional[DependencyCheckResult]:
        """获取缓存的检查结果"""
        pass
    
    def clear_cache(self, strategy_id: Optional[str] = None) -> None:
        """清除检查缓存"""
        pass
```

## 2. 策略验证器 (StrategyValidator)

### 2.1 类设计

```python
from typing import Type, Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ValidationType(Enum):
    SYNTAX = "syntax"
    METHODS = "methods"
    PARAMETERS = "parameters"
    RISK_RULES = "risk_rules"
    COMPATIBILITY = "compatibility"
    PERFORMANCE = "performance"

class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationIssue:
    validation_type: ValidationType
    severity: ValidationSeverity
    message: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    strategy_path: str
    is_valid: bool
    issues: List[ValidationIssue]
    validation_time: datetime
    validator_version: str
    summary: Dict[str, int]  # 按严重程度统计

class StrategyValidator:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.strict_mode = config.get("strategy_management.validation.strict_mode", False)
        self.skip_syntax_check = config.get("strategy_management.validation.skip_syntax_check", False)
        self.required_methods = [
            "on_init", "on_start", "on_stop", "on_tick"
        ]
        self.optional_methods = [
            "on_bar", "on_order", "on_trade"
        ]
    
    async def validate_syntax(self, strategy_path: str) -> ValidationResult:
        """验证策略代码语法"""
        pass
    
    async def validate_required_methods(self, strategy_class: Type) -> ValidationResult:
        """验证必需方法存在性"""
        pass
    
    async def validate_parameters(self, params: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
        """验证参数配置"""
        pass
    
    async def validate_risk_rules(self, strategy_config: Dict[str, Any]) -> ValidationResult:
        """验证风险控制规则"""
        pass
    
    async def validate_compatibility(self, strategy_class: Type) -> ValidationResult:
        """验证策略兼容性"""
        pass
    
    async def run_full_validation(self, strategy_path: str, params: Dict[str, Any]) -> ValidationResult:
        """运行完整验证"""
        pass
    
    def create_parameter_schema(self, strategy_class: Type) -> Dict[str, Any]:
        """创建参数验证模式"""
        pass
```

## 3. 策略健康监控器 (StrategyHealthMonitor)

### 3.1 类设计

```python
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class AnomalyType(Enum):
    HIGH_ERROR_RATE = "high_error_rate"
    SLOW_RESPONSE = "slow_response"
    MEMORY_LEAK = "memory_leak"
    EXCESSIVE_ORDERS = "excessive_orders"
    NO_ACTIVITY = "no_activity"
    UNUSUAL_PNL = "unusual_pnl"

@dataclass
class HealthMetric:
    name: str
    value: float
    unit: str
    timestamp: datetime
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

@dataclass
class Anomaly:
    anomaly_type: AnomalyType
    severity: HealthStatus
    description: str
    detected_at: datetime
    metrics: List[HealthMetric]
    suggested_actions: List[str]

@dataclass
class HealthReport:
    strategy_uuid: str
    strategy_name: str
    overall_status: HealthStatus
    metrics: List[HealthMetric]
    anomalies: List[Anomaly]
    uptime: timedelta
    last_check: datetime
    next_check: datetime
    recommendations: List[str]

class StrategyHealthMonitor:
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        self.check_interval = config.get("strategy_management.health_monitor.check_interval", 60)
        self.alert_threshold = config.get("strategy_management.health_monitor.alert_threshold", 5)
        self.auto_recovery = config.get("strategy_management.health_monitor.auto_recovery", True)
        
        self._monitored_strategies: Dict[str, Dict[str, Any]] = {}
        self._health_history: Dict[str, List[HealthReport]] = {}
        self._anomaly_detectors: List[Callable] = []
        self._recovery_handlers: Dict[AnomalyType, Callable] = {}
        
        self._setup_default_detectors()
        self._setup_default_recovery_handlers()
    
    async def start_monitoring(self, strategy_uuid: str) -> None:
        """开始监控策略"""
        pass
    
    async def stop_monitoring(self, strategy_uuid: str) -> None:
        """停止监控策略"""
        pass
    
    async def check_strategy_health(self, strategy_uuid: str) -> HealthReport:
        """检查策略健康状态"""
        pass
    
    async def detect_anomalies(self, strategy_uuid: str) -> List[Anomaly]:
        """检测异常"""
        pass
    
    async def attempt_recovery(self, strategy_uuid: str, anomaly: Anomaly) -> bool:
        """尝试恢复策略"""
        pass
    
    def generate_health_report(self, strategy_uuid: str) -> HealthReport:
        """生成健康报告"""
        pass
    
    def add_anomaly_detector(self, detector: Callable[[str], List[Anomaly]]) -> None:
        """添加异常检测器"""
        pass
    
    def add_recovery_handler(self, anomaly_type: AnomalyType, handler: Callable) -> None:
        """添加恢复处理器"""
        pass
    
    def get_health_history(self, strategy_uuid: str, time_range: Optional[tuple] = None) -> List[HealthReport]:
        """获取健康历史"""
        pass
    
    def _setup_default_detectors(self) -> None:
        """设置默认异常检测器"""
        pass
    
    def _setup_default_recovery_handlers(self) -> None:
        """设置默认恢复处理器"""
        pass
```

## 4. 策略事件处理器 (StrategyEventHandler)

### 4.1 类设计

```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

@dataclass
class EventFilter:
    event_types: Optional[List[str]] = None
    strategy_uuids: Optional[List[str]] = None
    time_range: Optional[tuple] = None
    severity_levels: Optional[List[str]] = None

@dataclass
class EventAggregate:
    event_type: str
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    strategies_affected: List[str]
    summary: Dict[str, Any]

class StrategyEventHandler:
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        self.async_processing = config.get("strategy_management.event_handling.async_processing", True)
        self.buffer_size = config.get("strategy_management.event_handling.event_buffer_size", 1000)
        self.persistence_enabled = config.get("strategy_management.event_handling.persistence_enabled", True)
        self.replay_enabled = config.get("strategy_management.event_handling.replay_enabled", True)
        
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._event_buffer: List[Event] = []
        self._event_store: Optional[Any] = None  # 事件存储后端
        
        self._setup_event_subscriptions()
    
    async def handle_strategy_event(self, event: Event) -> None:
        """处理策略事件"""
        pass
    
    def route_event(self, event: Event) -> List[str]:
        """路由事件到相应处理器"""
        pass
    
    async def persist_event(self, event: Event) -> None:
        """持久化事件"""
        pass
    
    async def replay_events(self, strategy_uuid: str, time_range: tuple) -> List[Event]:
        """回放事件"""
        pass
    
    def filter_events(self, events: List[Event], filter_criteria: EventFilter) -> List[Event]:
        """过滤事件"""
        pass
    
    def aggregate_events(self, events: List[Event], group_by: str) -> List[EventAggregate]:
        """聚合事件"""
        pass
    
    def register_handler(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """注册事件处理器"""
        pass
    
    def unregister_handler(self, event_type: str, handler: Callable) -> None:
        """注销事件处理器"""
        pass
    
    def get_event_statistics(self, time_range: Optional[tuple] = None) -> Dict[str, Any]:
        """获取事件统计"""
        pass
    
    def _setup_event_subscriptions(self) -> None:
        """设置事件订阅"""
        pass
```

## 5. 增强的策略工厂

### 5.1 修改现有 StrategyFactory 类

```python
class EnhancedStrategyFactory(StrategyFactory):
    def __init__(self):
        super().__init__()
        self.dependency_checker: Optional[DependencyChecker] = None
        self.strategy_validator: Optional[StrategyValidator] = None
        self.validation_cache: Dict[str, ValidationResult] = {}
        self.dependency_cache: Dict[str, DependencyCheckResult] = {}
    
    def set_dependency_checker(self, checker: DependencyChecker) -> None:
        """设置依赖检查器"""
        self.dependency_checker = checker
    
    def set_strategy_validator(self, validator: StrategyValidator) -> None:
        """设置策略验证器"""
        self.strategy_validator = validator
    
    async def pre_validate_strategy(self, strategy_path: str, params: Dict[str, Any]) -> tuple[bool, str]:
        """预验证策略"""
        pass
    
    async def check_strategy_dependencies(self, strategy_config: Dict[str, Any]) -> tuple[bool, str]:
        """检查策略依赖"""
        pass
    
    async def create_strategy_with_validation(self, 
                                            strategy_type: str, 
                                            strategy_id: str, 
                                            event_bus, 
                                            params: Dict[str, Any] = None,
                                            skip_validation: bool = False) -> tuple[Optional[BaseStrategy], str]:
        """创建策略并进行验证"""
        pass
    
    def get_validation_report(self, strategy_type: str) -> Optional[ValidationResult]:
        """获取验证报告"""
        pass
    
    def get_dependency_report(self, strategy_id: str) -> Optional[DependencyCheckResult]:
        """获取依赖检查报告"""
        pass
    
    def clear_validation_cache(self) -> None:
        """清除验证缓存"""
        pass
```

## 6. 新增事件类型

### 6.1 扩展 EventType 类

```python
class EventType:
    # ... 现有事件类型 ...
    
    # 新增策略验证相关事件
    STRATEGY_DEPENDENCY_CHECK = "strategy.dependency_check"
    STRATEGY_DEPENDENCY_PASSED = "strategy.dependency_passed"
    STRATEGY_DEPENDENCY_FAILED = "strategy.dependency_failed"
    STRATEGY_VALIDATION_STARTED = "strategy.validation_started"
    STRATEGY_VALIDATION_PASSED = "strategy.validation_passed"
    STRATEGY_VALIDATION_FAILED = "strategy.validation_failed"
    
    # 新增策略健康监控事件
    STRATEGY_HEALTH_CHECK = "strategy.health_check"
    STRATEGY_HEALTH_WARNING = "strategy.health_warning"
    STRATEGY_HEALTH_CRITICAL = "strategy.health_critical"
    STRATEGY_ANOMALY_DETECTED = "strategy.anomaly_detected"
    STRATEGY_RECOVERY_STARTED = "strategy.recovery_started"
    STRATEGY_RECOVERY_SUCCESS = "strategy.recovery_success"
    STRATEGY_RECOVERY_FAILED = "strategy.recovery_failed"
    
    # 新增策略性能事件
    STRATEGY_PERFORMANCE_ALERT = "strategy.performance_alert"
    STRATEGY_PERFORMANCE_REPORT = "strategy.performance_report"
    
    # 新增策略生命周期事件
    STRATEGY_LIFECYCLE_CHANGED = "strategy.lifecycle_changed"
    STRATEGY_CONFIG_UPDATED = "strategy.config_updated"
    STRATEGY_DEPENDENCY_UPDATED = "strategy.dependency_updated"
```

## 7. 配置数据结构

### 7.1 配置模式定义

```yaml
# config/system.yaml 新增部分
strategy_management:
  # 依赖检查配置
  dependency_check:
    enabled: true
    timeout: 30  # 秒
    retry_count: 3
    cache_duration: 300  # 秒
    parallel_checks: true
    
    # 具体检查项配置
    checks:
      gateway_connection:
        enabled: true
        timeout: 10
      contract_info:
        enabled: true
        timeout: 5
      account_balance:
        enabled: true
        minimum_margin_ratio: 0.2
      market_hours:
        enabled: true
        allow_pre_market: false
      risk_limits:
        enabled: true
        max_position_size: 1000000
      data_feed:
        enabled: true
        timeout: 15
  
  # 策略验证配置
  validation:
    enabled: true
    strict_mode: false
    skip_syntax_check: false
    cache_results: true
    
    # 验证规则配置
    rules:
      required_methods: ["on_init", "on_start", "on_stop", "on_tick"]
      optional_methods: ["on_bar", "on_order", "on_trade"]
      max_file_size: 1048576  # 1MB
      max_complexity: 100
  
  # 健康监控配置
  health_monitor:
    enabled: true
    check_interval: 60  # 秒
    alert_threshold: 5  # 连续失败次数
    auto_recovery: true
    history_retention: 7  # 天
    
    # 监控指标配置
    metrics:
      error_rate_threshold: 0.1
      response_time_threshold: 1000  # 毫秒
      memory_usage_threshold: 0.8
      order_rate_threshold: 100  # 每分钟
    
    # 异常检测配置
    anomaly_detection:
      enabled: true
      sensitivity: "medium"  # low, medium, high
      window_size: 300  # 秒
  
  # 事件处理配置
  event_handling:
    async_processing: true
    event_buffer_size: 1000
    persistence_enabled: true
    replay_enabled: true
    
    # 事件存储配置
    storage:
      backend: "sqlite"  # sqlite, redis, mongodb
      connection_string: "sqlite:///strategy_events.db"
      retention_days: 30
    
    # 事件过滤配置
    filters:
      max_events_per_second: 1000
      duplicate_suppression: true
      priority_boost: true
```

## 8. API 接口规范

### 8.1 新增 REST API 端点

```python
# 策略健康相关 API
GET /api/v1/strategies/{uuid}/health
# 响应: HealthReport

GET /api/v1/strategies/{uuid}/dependencies
# 响应: DependencyCheckResult

POST /api/v1/strategies/{uuid}/validate
# 请求体: {"force_recheck": bool}
# 响应: ValidationResult

POST /api/v1/strategies/{uuid}/recover
# 请求体: {"recovery_type": str, "force": bool}
# 响应: {"success": bool, "message": str}

GET /api/v1/strategies/{uuid}/events
# 查询参数: start_time, end_time, event_types, limit
# 响应: List[Event]

GET /api/v1/strategies/validation-report
# 响应: Dict[str, ValidationResult]

GET /api/v1/strategies/health-summary
# 响应: Dict[str, HealthStatus]

# 系统级 API
GET /api/v1/system/dependency-status
# 响应: 系统依赖状态概览

POST /api/v1/system/clear-cache
# 请求体: {"cache_type": str}  # validation, dependency, all
# 响应: {"success": bool, "message": str}
```

## 9. 数据库模式 (如果使用持久化)

### 9.1 事件存储表结构

```sql
CREATE TABLE strategy_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id VARCHAR(36) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    strategy_uuid VARCHAR(36),
    strategy_id VARCHAR(100),
    event_data TEXT,  -- JSON
    source VARCHAR(100),
    priority INTEGER,
    timestamp BIGINT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_uuid (strategy_uuid),
    INDEX idx_event_type (event_type),
    INDEX idx_timestamp (timestamp)
);

CREATE TABLE strategy_health_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_uuid VARCHAR(36) NOT NULL,
    health_status VARCHAR(20) NOT NULL,
    metrics TEXT,  -- JSON
    anomalies TEXT,  -- JSON
    check_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_uuid (strategy_uuid),
    INDEX idx_check_time (check_time)
);

CREATE TABLE validation_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_path VARCHAR(500) NOT NULL,
    strategy_hash VARCHAR(64) NOT NULL,
    validation_result TEXT,  -- JSON
    validation_time DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_path (strategy_path),
    INDEX idx_expires_at (expires_at)
);
```

## 10. 错误处理和异常定义

### 10.1 自定义异常类

```python
class StrategyValidationError(Exception):
    """策略验证错误"""
    def __init__(self, message: str, validation_result: Optional[ValidationResult] = None):
        super().__init__(message)
        self.validation_result = validation_result

class DependencyCheckError(Exception):
    """依赖检查错误"""
    def __init__(self, message: str, check_result: Optional[DependencyCheckResult] = None):
        super().__init__(message)
        self.check_result = check_result

class StrategyHealthError(Exception):
    """策略健康检查错误"""
    def __init__(self, message: str, health_report: Optional[HealthReport] = None):
        super().__init__(message)
        self.health_report = health_report

class StrategyRecoveryError(Exception):
    """策略恢复错误"""
    def __init__(self, message: str, recovery_attempts: int = 0):
        super().__init__(message)
        self.recovery_attempts = recovery_attempts
```

这个技术规范提供了详细的类设计、方法签名、数据结构和配置选项，为实施提供了清晰的指导。
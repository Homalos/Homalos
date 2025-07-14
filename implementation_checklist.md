# 策略增强实施清单

## 阶段1: 依赖验证框架实施

### 1.1 创建依赖检查器 (DependencyChecker)

**文件**: `src/strategies/dependency_checker.py`

**实施步骤**:
1. 创建 `DependencyChecker` 基类
2. 实现网关连接状态检查方法
3. 实现合约信息验证方法
4. 实现账户资金检查方法
5. 实现市场时间验证方法
6. 添加依赖检查结果数据结构
7. 实现异步检查机制
8. 添加检查超时和重试逻辑

**关键方法**:
- `check_gateway_connection(gateway_name: str) -> bool`
- `check_contract_info(symbol: str) -> bool`
- `check_account_balance(required_margin: float) -> bool`
- `check_market_hours(symbol: str) -> bool`
- `run_all_checks(strategy_config: dict) -> DependencyCheckResult`

### 1.2 创建策略验证器 (StrategyValidator)

**文件**: `src/strategies/strategy_validator.py`

**实施步骤**:
1. 创建 `StrategyValidator` 类
2. 实现策略代码语法检查
3. 实现必需方法存在性验证
4. 实现参数配置验证
5. 实现风险控制规则检查
6. 添加验证结果报告机制
7. 实现策略兼容性检查

**关键方法**:
- `validate_syntax(strategy_path: str) -> ValidationResult`
- `validate_required_methods(strategy_class: type) -> ValidationResult`
- `validate_parameters(params: dict, schema: dict) -> ValidationResult`
- `validate_risk_rules(strategy_config: dict) -> ValidationResult`
- `run_full_validation(strategy_path: str, params: dict) -> ValidationResult`

### 1.3 增强策略工厂

**修改文件**: `src/strategies/strategy_factory.py`

**实施步骤**:
1. 集成 `DependencyChecker` 到策略创建流程
2. 集成 `StrategyValidator` 到策略加载流程
3. 添加预验证缓存机制
4. 实现验证失败的详细错误报告
5. 添加验证跳过选项（用于紧急情况）
6. 更新 `create_strategy` 方法
7. 更新 `validate_strategy_config` 方法

**新增方法**:
- `pre_validate_strategy(strategy_path: str, params: dict) -> bool`
- `check_strategy_dependencies(strategy_instance: BaseStrategy) -> bool`
- `get_validation_report(strategy_type: str) -> dict`

## 阶段2: 事件驱动管理实施

### 2.1 扩展事件系统

**修改文件**: `src/core/event.py`

**实施步骤**:
1. 添加新的策略相关事件类型
2. 创建策略事件数据结构
3. 实现事件优先级调整
4. 添加事件追踪机制

**新增事件类型**:
- `STRATEGY_DEPENDENCY_CHECK`
- `STRATEGY_DEPENDENCY_FAILED`
- `STRATEGY_VALIDATION_PASSED`
- `STRATEGY_VALIDATION_FAILED`
- `STRATEGY_HEALTH_CHECK`
- `STRATEGY_RECOVERY_ATTEMPT`
- `STRATEGY_PERFORMANCE_ALERT`

### 2.2 创建策略健康监控器

**文件**: `src/strategies/strategy_health_monitor.py`

**实施步骤**:
1. 创建 `StrategyHealthMonitor` 类
2. 实现策略状态监控机制
3. 实现异常检测算法
4. 实现自动恢复逻辑
5. 实现性能指标收集
6. 实现健康报告生成
7. 集成事件总线通信
8. 添加监控配置管理

**关键方法**:
- `start_monitoring(strategy_uuid: str) -> None`
- `stop_monitoring(strategy_uuid: str) -> None`
- `check_strategy_health(strategy_uuid: str) -> HealthStatus`
- `detect_anomalies(strategy_uuid: str) -> List[Anomaly]`
- `attempt_recovery(strategy_uuid: str) -> bool`
- `generate_health_report(strategy_uuid: str) -> HealthReport`

### 2.3 创建策略事件处理器

**文件**: `src/strategies/strategy_event_handler.py`

**实施步骤**:
1. 创建 `StrategyEventHandler` 类
2. 实现事件路由机制
3. 实现事件分发逻辑
4. 实现事件持久化
5. 实现事件回放功能
6. 添加事件过滤器
7. 实现事件聚合功能

**关键方法**:
- `handle_strategy_event(event: Event) -> None`
- `route_event(event: Event) -> str`
- `persist_event(event: Event) -> None`
- `replay_events(strategy_uuid: str, time_range: tuple) -> List[Event]`
- `filter_events(events: List[Event], criteria: dict) -> List[Event]`

### 2.4 增强策略管理器

**修改文件**: `src/services/trading_engine.py` (StrategyManager类)

**实施步骤**:
1. 集成健康监控器
2. 集成事件处理器
3. 添加策略恢复机制
4. 实现策略性能追踪
5. 添加策略生命周期事件发布
6. 实现策略依赖检查集成

**新增方法**:
- `enable_health_monitoring(strategy_uuid: str) -> None`
- `handle_strategy_failure(strategy_uuid: str, error: Exception) -> None`
- `recover_strategy(strategy_uuid: str) -> bool`
- `get_strategy_performance(strategy_uuid: str) -> dict`

## 阶段3: 集成和优化

### 3.1 系统集成

**实施步骤**:
1. 更新 `start.py` 集成新组件
2. 修改 Web API 支持新功能
3. 更新配置文件支持新选项
4. 集成到现有的策略加载流程
5. 测试端到端功能

### 3.2 性能优化

**实施步骤**:
1. 优化依赖检查性能
2. 优化事件处理性能
3. 实现检查结果缓存
4. 优化监控频率
5. 减少不必要的验证开销

### 3.3 配置管理

**修改文件**: `config/system.yaml`

**新增配置项**:
```yaml
strategy_management:
  dependency_check:
    enabled: true
    timeout: 30
    retry_count: 3
    cache_duration: 300
    
  validation:
    enabled: true
    strict_mode: false
    skip_syntax_check: false
    
  health_monitor:
    enabled: true
    check_interval: 60
    alert_threshold: 5
    auto_recovery: true
    
  event_handling:
    async_processing: true
    event_buffer_size: 1000
    persistence_enabled: true
    replay_enabled: true
```

### 3.4 Web API 增强

**修改文件**: `src/web/web_server.py`

**新增API端点**:
- `GET /api/v1/strategies/{uuid}/health` - 获取策略健康状态
- `GET /api/v1/strategies/{uuid}/dependencies` - 获取策略依赖检查结果
- `POST /api/v1/strategies/{uuid}/validate` - 手动触发策略验证
- `POST /api/v1/strategies/{uuid}/recover` - 手动触发策略恢复
- `GET /api/v1/strategies/{uuid}/events` - 获取策略事件历史
- `GET /api/v1/strategies/validation-report` - 获取全局验证报告

## 测试计划

### 单元测试
1. `test_dependency_checker.py`
2. `test_strategy_validator.py`
3. `test_strategy_health_monitor.py`
4. `test_strategy_event_handler.py`

### 集成测试
1. `test_enhanced_strategy_factory.py`
2. `test_strategy_lifecycle_with_validation.py`
3. `test_event_driven_management.py`

### 端到端测试
1. `test_complete_strategy_workflow.py`
2. `test_failure_recovery_scenarios.py`
3. `test_performance_under_load.py`

## 文档计划

1. **用户指南**: 如何使用新的策略验证和监控功能
2. **开发者指南**: 如何扩展验证规则和监控指标
3. **API文档**: 新增API端点的详细说明
4. **配置指南**: 新配置选项的说明和最佳实践
5. **故障排除指南**: 常见问题和解决方案

## 里程碑

- **里程碑1** (第1-2周): 完成依赖验证框架
- **里程碑2** (第3-4周): 完成事件驱动管理
- **里程碑3** (第5周): 完成系统集成
- **里程碑4** (第6周): 完成测试和文档

## 成功标准

1. **功能完整性**: 所有计划功能正常工作
2. **性能要求**: 验证开销不超过策略启动时间的20%
3. **稳定性**: 连续运行24小时无崩溃
4. **可用性**: 用户可以轻松理解和使用新功能
5. **兼容性**: 现有策略无需修改即可使用新功能
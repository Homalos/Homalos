// 国际化模块
// 支持简体中文和英文切换

// 语言包
const messages = {
    'zh-CN': {
        // 通用
        common: {
            loading: '加载中...',
            confirm: '确认',
            cancel: '取消',
            save: '保存',
            delete: '删除',
            edit: '编辑',
            add: '添加',
            search: '搜索',
            refresh: '刷新',
            copy: '复制',
            success: '成功',
            error: '错误',
            warning: '警告',
            info: '信息',
            author: '作者',
            configParams: '配置策略参数',
            optional: '可选',
            params: '策略参数',
            jsonParamsHint: '请输入JSON格式的策略参数（可选）',
            preview: '预览信息',
            filePath: '文件路径',
            strategyClass: '策略类',
            isTemplate: '是否模板',
            yes: '是',
            no: '否',
            paramsPreview: '参数预览',
            note: '说明',
            autoGenerateUuid: '系统将自动生成策略UUID作为唯一标识',
            rescan: '重新扫描',
            close: '关闭',
            jsonFormatError: 'JSON格式错误',
            getStrategyListFailed: '获取策略列表失败',
            allStrategiesLoaded: '所有策略都已加载，没有新的策略可以加载',
            foundStrategies: '发现 {count} 个可加载的策略文件',
            pleaseSelectStrategy: '请选择策略文件',
            scanningStrategies: '正在扫描策略文件...',
            noStrategyFiles: '未发现任何策略文件，请检查策略目录',
            allStrategiesLoadedWithCount: '所有 {count} 个策略都已加载，暂无新策略可加载',
            noAvailableStrategies: '暂无可加载的策略文件，请检查策略目录或点击重新扫描'
        },
        
        // 头部
        header: {
            title: 'Homalos量化交易系统',
            subtitle: '基于Python的期货量化交易系统 v2.0',
            language: '语言'
        },
        
        // 导航菜单
        navigation: {
            home: '主页',
            eventMonitor: '事件监控',
            dashboard: '监控仪表板'
        },
        
        // 仪表板
        dashboard: {
            systemStatus: '系统状态',
            strategyCount: '策略数量',
            accountBalance: '账户余额',
            connectionStatus: '连接状态',
            running: '运行中',
            stopped: '已停止',
            connected: '已连接',
            disconnected: '断开'
        },
        
        // 策略管理
        strategy: {
            management: '策略管理',
            loadStrategy: '加载策略',
            strategyName: '策略名称',
            strategyUuid: '策略UUID',
            status: '状态',
            startTime: '启动时间',
            actions: '操作',
            start: '启动',
            stop: '停止',
            noStrategies: '暂无策略',
            loadFirstStrategy: '加载第一个策略',
            startSuccess: '策略启动成功',
            stopSuccess: '策略停止成功',
            startFailed: '启动策略失败',
            stopFailed: '停止策略失败',
            copyUuid: '复制UUID',
            uuidCopied: 'UUID已复制到剪贴板'
        },
        
        // 策略对话框
        strategyDialog: {
            title: '加载策略',
            selectStrategy: '选择策略文件',
            pleaseSelect: '请选择一个策略',
            loadSuccess: '策略加载成功',
            loadFailed: '策略加载失败',
            noAvailableStrategies: '没有可用的策略'
        },
        
        // 日志相关
        log: {
            realtimeLog: '实时日志',
            autoScroll: '自动滚动',
            pauseScroll: '暂停滚动',
            clear: '清空',
            logLevel: '日志级别',
            info: '信息',
            success: '成功',
            warning: '警告',
            error: '错误',
            noLogs: '暂无日志信息',
            systemWillShowLogs: '系统将在这里显示实时日志',
            noLogsWithFilter: '当前过滤条件下无日志显示',
            totalLogs: '总日志数',
            displayedLogs: '显示数',
            errorCount: '错误数',
            warningCount: '警告数',
            confirmClearLogs: '确定要清空所有日志吗？',
            confirmOperation: '确认操作',
            logsCleared: '日志已清空'
        },
        
        // 语言切换器
        languageSwitcher: {
            switchSuccess: '语言已切换为简体中文'
        },
        
        // 日志面板
        logs: {
            title: '实时日志',
            clear: '清空日志',
            noLogs: '暂无日志',
            wsConnected: 'WebSocket 已连接',
            wsDisconnected: 'WebSocket 已断开',
            systemInitializing: '正在初始化系统...',
            systemInitialized: '应用初始化完成',
            systemInitFailed: '应用初始化失败',
            dataRefreshFailed: '数据刷新失败'
        },
        
        // 系统消息
        system: {
            initializingSystem: '正在初始化系统...',
            appInitialized: '应用初始化完成',
            appInitFailed: '应用初始化失败'
        },
        
        // 版权信息
        footer: {
            copyright: '© 2025 Homalos量化交易系统'
        }
    },
    
    'en': {
        // Common
        common: {
            loading: 'Loading...',
            confirm: 'Confirm',
            cancel: 'Cancel',
            save: 'Save',
            delete: 'Delete',
            edit: 'Edit',
            add: 'Add',
            search: 'Search',
            refresh: 'Refresh',
            copy: 'Copy',
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Info',
            author: 'Author',
            configParams: 'Configure Strategy Parameters',
            optional: 'Optional',
            params: 'Strategy Parameters',
            jsonParamsHint: 'Please enter strategy parameters in JSON format (optional)',
            preview: 'Preview Information',
            filePath: 'File Path',
            strategyClass: 'Strategy Class',
            isTemplate: 'Is Template',
            yes: 'Yes',
            no: 'No',
            paramsPreview: 'Parameters Preview',
            note: 'Note',
            autoGenerateUuid: 'System will automatically generate strategy UUID as unique identifier',
            rescan: 'Rescan',
            close: 'Close',
            jsonFormatError: 'JSON format error',
            getStrategyListFailed: 'Failed to get strategy list',
            allStrategiesLoaded: 'All strategies are loaded, no new strategies available',
            foundStrategies: 'Found {count} loadable strategy files',
            pleaseSelectStrategy: 'Please select a strategy file',
            scanningStrategies: 'Scanning strategy files...',
            noStrategyFiles: 'No strategy files found, please check strategy directory',
            allStrategiesLoadedWithCount: 'All {count} strategies are loaded, no new strategies available',
            noAvailableStrategies: 'No loadable strategy files available, please check strategy directory or click rescan'
        },
        
        // Header
        header: {
            title: 'Homalos Quantitative Trading System',
            subtitle: 'Python-based Futures Quantitative Trading System v2.0',
            language: 'Language'
        },
        
        // Navigation
        navigation: {
            home: 'Home',
            eventMonitor: 'Event Monitor',
            dashboard: 'Monitor Dashboard'
        },
        
        // Dashboard
        dashboard: {
            systemStatus: 'System Status',
            strategyCount: 'Strategy Count',
            accountBalance: 'Account Balance',
            connectionStatus: 'Connection Status',
            running: 'Running',
            stopped: 'Stopped',
            connected: 'Connected',
            disconnected: 'Disconnected'
        },
        
        // Strategy
        strategy: {
            management: 'Strategy Management',
            loadStrategy: 'Load Strategy',
            strategyName: 'Strategy Name',
            strategyUuid: 'Strategy UUID',
            status: 'Status',
            startTime: 'Start Time',
            actions: 'Actions',
            start: 'Start',
            stop: 'Stop',
            noStrategies: 'No strategies',
            loadFirstStrategy: 'Load first strategy',
            startSuccess: 'Strategy started successfully',
            stopSuccess: 'Strategy stopped successfully',
            startFailed: 'Failed to start strategy',
            stopFailed: 'Failed to stop strategy',
            copyUuid: 'Copy UUID',
            uuidCopied: 'UUID copied to clipboard'
        },
        
        // Strategy Dialog
        strategyDialog: {
            title: 'Load Strategy',
            selectStrategy: 'Select Strategy File',
            pleaseSelect: 'Please select a strategy',
            loadSuccess: 'Strategy loaded successfully',
            loadFailed: 'Failed to load strategy',
            noAvailableStrategies: 'No available strategies'
        },
        
        // Log related
        log: {
            realtimeLog: 'Real-time Logs',
            autoScroll: 'Auto Scroll',
            pauseScroll: 'Pause Scroll',
            clear: 'Clear',
            logLevel: 'Log Level',
            info: 'Info',
            success: 'Success',
            warning: 'Warning',
            error: 'Error',
            noLogs: 'No log information',
            systemWillShowLogs: 'System will display real-time logs here',
            noLogsWithFilter: 'No logs to display with current filter',
            totalLogs: 'Total Logs',
            displayedLogs: 'Displayed',
            errorCount: 'Errors',
            warningCount: 'Warnings',
            confirmClearLogs: 'Are you sure you want to clear all logs?',
            confirmOperation: 'Confirm Operation',
            logsCleared: 'Logs cleared'
        },
        
        // Language Switcher
        languageSwitcher: {
            switchSuccess: 'Language switched to English'
        },
        
        // Logs
        logs: {
            title: 'Real-time Logs',
            clear: 'Clear Logs',
            noLogs: 'No logs',
            wsConnected: 'WebSocket connected',
            wsDisconnected: 'WebSocket disconnected',
            systemInitializing: 'Initializing system...',
            systemInitialized: 'Application initialized',
            systemInitFailed: 'Application initialization failed',
            dataRefreshFailed: 'Data refresh failed'
        },
        
        // System
        system: {
            initializingSystem: 'Initializing system...',
            appInitialized: 'Application initialized',
            appInitFailed: 'Application initialization failed'
        },
        
        // Footer
        footer: {
            copyright: '© 2025 Homalos Quantitative Trading System'
        }
    }
}

// 当前语言
let currentLocale = 'zh-CN'

// 响应式语言状态
const i18nState = Vue.reactive({
    locale: currentLocale,
    messages: messages[currentLocale]
})

// 国际化工具函数
const i18n = {
    // 获取当前语言
    getLocale() {
        return i18nState.locale
    },
    
    // 设置语言
    setLocale(locale) {
        if (messages[locale]) {
            i18nState.locale = locale
            i18nState.messages = messages[locale]
            currentLocale = locale
            
            // 保存到本地存储
            localStorage.setItem('homalos-locale', locale)
            
            // 更新HTML lang属性
            document.documentElement.lang = locale
            
            console.log(`语言已切换到: ${locale}`)
        } else {
            console.warn(`不支持的语言: ${locale}`)
        }
    },
    
    // 获取翻译文本
    t(key, params = {}) {
        const keys = key.split('.')
        let value = i18nState.messages
        
        for (const k of keys) {
            if (value && typeof value === 'object' && k in value) {
                value = value[k]
            } else {
                console.warn(`翻译键不存在: ${key}`)
                return key
            }
        }
        
        // 如果有参数，进行替换
        if (typeof value === 'string' && Object.keys(params).length > 0) {
            return value.replace(/\{(\w+)\}/g, (match, paramKey) => {
                return params[paramKey] !== undefined ? params[paramKey] : match
            })
        }
        
        return value || key
    },
    
    // 获取可用语言列表
    getAvailableLocales() {
        return Object.keys(messages)
    },
    
    // 获取语言显示名称
    getLocaleDisplayName(locale) {
        const names = {
            'zh-CN': '简体中文',
            'en': 'English'
        }
        return names[locale] || locale
    },
    
    // 初始化
    init() {
        // 从本地存储读取语言设置
        const savedLocale = localStorage.getItem('homalos-locale')
        if (savedLocale && messages[savedLocale]) {
            this.setLocale(savedLocale)
        } else {
            // 检测浏览器语言
            const browserLang = navigator.language || navigator.userLanguage
            if (browserLang.startsWith('zh')) {
                this.setLocale('zh-CN')
            } else {
                this.setLocale('en')
            }
        }
    }
}

// 用于组合式API的工具函数
function useI18n() {
    return {
        locale: Vue.computed(() => i18nState.locale),
        t: i18n.t.bind(i18n),
        setLocale: i18n.setLocale.bind(i18n),
        getAvailableLocales: i18n.getAvailableLocales.bind(i18n),
        getLocaleDisplayName: i18n.getLocaleDisplayName.bind(i18n)
    }
}

// 全局导出
window.i18n = i18n
window.i18nState = i18nState
window.useI18n = useI18n

// 初始化
i18n.init()

console.log('🌐 国际化模块已加载')
// Vue组件注册脚本
// 等待DOM和Vue加载完成后注册所有组件

document.addEventListener('DOMContentLoaded', () => {
    // 检查Vue和ElementPlus是否已加载
    if (typeof Vue === 'undefined') {
        console.error('Vue 3 未加载')
        return
    }
    
    if (typeof ElementPlus === 'undefined') {
        console.error('ElementPlus 未加载')
        return
    }
    
    console.log('开始注册Vue组件...')
    
    // 等待所有组件脚本加载完成
    const checkComponentsLoaded = () => {
        const componentsToCheck = [
            'DashboardComponent',
            'StrategyTableComponent', 
            'StrategyDialogComponent',
            'LogPanelComponent',
            'LanguageSwitcherComponent'
        ]
        
        const allLoaded = componentsToCheck.every(name => 
            window[name] !== undefined
        )
        
        if (allLoaded) {
            registerAllComponents()
        } else {
            // 如果组件还未加载完成，等待一段时间后重试
            setTimeout(checkComponentsLoaded, 100)
        }
    }
    
    // 注册所有组件
    const registerAllComponents = () => {
        try {
            // 全局组件注册
            const { createApp } = Vue
            
            // 创建临时应用用于注册组件
            const tempApp = createApp({})
            
            // 注册组件
            if (window.DashboardComponent) {
                tempApp.component('dashboard-component', window.DashboardComponent)
                console.log('✅ DashboardComponent 已注册')
            }
            
            if (window.StrategyTableComponent) {
                tempApp.component('strategy-table-component', window.StrategyTableComponent)
                console.log('✅ StrategyTableComponent 已注册')
            }
            
            if (window.StrategyDialogComponent) {
                tempApp.component('strategy-dialog-component', window.StrategyDialogComponent)
                console.log('✅ StrategyDialogComponent 已注册')
            }
            
            if (window.LogPanelComponent) {
                tempApp.component('log-panel-component', window.LogPanelComponent)
                console.log('✅ LogPanelComponent 已注册')
            }
            
            if (window.LanguageSwitcherComponent) {
                tempApp.component('language-switcher-component', window.LanguageSwitcherComponent)
                console.log('✅ LanguageSwitcherComponent 已注册')
            }
            
            // 将注册的组件存储到全局，供主应用使用
            window.VueComponentRegistry = {
                DashboardComponent: window.DashboardComponent,
                StrategyTableComponent: window.StrategyTableComponent,
                StrategyDialogComponent: window.StrategyDialogComponent,
                LogPanelComponent: window.LogPanelComponent,
                LanguageSwitcherComponent: window.LanguageSwitcherComponent
            }
            
            console.log('🎉 所有Vue组件注册完成')
            
            // 触发主应用启动事件
            window.dispatchEvent(new CustomEvent('componentsReady'))
            
        } catch (error) {
            console.error('组件注册失败:', error)
        }
    }
    
    // 开始检查组件是否已加载
    checkComponentsLoaded()
})

// 导出注册函数，供其他模块使用
window.registerVueComponents = () => {
    console.log('手动触发组件注册...')
    document.dispatchEvent(new Event('DOMContentLoaded'))
}
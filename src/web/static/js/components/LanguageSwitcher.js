// 语言切换组件
// 提供简体中文和英文切换功能

const LanguageSwitcherComponent = {
    name: 'LanguageSwitcherComponent',
    template: `
        <div class="language-switcher">
            <el-dropdown @command="handleLanguageChange" trigger="click">
                <el-button type="text" class="language-button">
                    <span class="language-icon">🌐</span>
                    <span class="language-text">{{ currentLanguageDisplay }}</span>
                    <span class="el-icon-arrow-down"></span>
                </el-button>
                <template #dropdown>
                    <el-dropdown-menu>
                        <el-dropdown-item 
                            v-for="locale in availableLocales" 
                            :key="locale"
                            :command="locale"
                            :class="{ 'is-active': locale === currentLocale }">
                            <span class="locale-flag">{{ getLocaleFlag(locale) }}</span>
                            <span class="locale-name">{{ getLocaleDisplayName(locale) }}</span>
                            <span v-if="locale === currentLocale" class="el-icon-check check-icon"></span>
                        </el-dropdown-item>
                    </el-dropdown-menu>
                </template>
            </el-dropdown>
        </div>
    `,
    
    setup() {
        const { locale, setLocale, getAvailableLocales, getLocaleDisplayName } = window.useI18n()
        
        // 当前语言
        const currentLocale = Vue.computed(() => locale.value)
        
        // 当前语言显示名称
        const currentLanguageDisplay = Vue.computed(() => {
            return getLocaleDisplayName(currentLocale.value)
        })
        
        // 可用语言列表
        const availableLocales = Vue.computed(() => {
            return getAvailableLocales()
        })
        
        // 获取语言对应的旗帜图标
        const getLocaleFlag = (locale) => {
            const flags = {
                'zh-CN': '🇨🇳',
                'en': '🇺🇸'
            }
            return flags[locale] || '🌐'
        }
        
        // 处理语言切换
        const handleLanguageChange = (locale) => {
            if (locale !== currentLocale.value) {
                setLocale(locale)
                
                // 显示切换成功消息 - 使用国际化
                const { t } = window.useI18n()
                const message = t('languageSwitcher.switchSuccess')
                    
                window.ElMessage.success({
                    message: message,
                    duration: 2000
                })
            }
        }
        
        return {
            currentLocale,
            currentLanguageDisplay,
            availableLocales,
            getLocaleFlag,
            getLocaleDisplayName,
            handleLanguageChange
        }
    }
}

// 导出到全局
window.LanguageSwitcherComponent = LanguageSwitcherComponent

console.log('🌐 语言切换组件已加载')
/**
 * ECharts配置文件
 */
import * as echarts from 'echarts/core'
import {
  LineChart,
  BarChart
} from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent
} from 'echarts/components'
import {
  CanvasRenderer
} from 'echarts/renderers'

// 注册必要的组件
echarts.use([
  LineChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer
])

export default echarts

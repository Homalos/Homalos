<template>
  <div class="return-rate-chart">
    <v-chart 
      :option="chartOption" 
      :style="{ height: '200px', width: '100%' }"
      autoresize
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../../plugins/echarts'

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
})

const chartOption = computed(() => {
  const dates = props.data.map(item => item.date)
  const rates = props.data.map(item => item.rate)

  return {
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        const value = params[0].value
        const color = value >= 0 ? '#F56C6C' : '#67C23A'  // 红涨绿跌
        const symbol = value >= 0 ? '+' : ''
        return `${params[0].axisValue}<br/>收益率: <span style="color: ${color}">${symbol}${value}%</span>`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: {
        fontSize: 10,
        color: '#666'
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10,
        color: '#666',
        formatter: function(value) {
          return value + '%'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#E4E7ED'
        }
      }
    },
    series: [
      {
        name: '收益率',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: {
          color: function(params) {
            // 根据整体趋势决定线条颜色
            const lastValue = rates[rates.length - 1]
            return lastValue >= 0 ? '#F56C6C' : '#67C23A'  // 红涨绿跌
          },
          width: 2
        },
        itemStyle: {
          color: function(params) {
            return params.value >= 0 ? '#F56C6C' : '#67C23A'  // 红涨绿跌
          }
        },
        areaStyle: {
          color: function(params) {
            // 根据整体趋势决定区域颜色
            const lastValue = rates[rates.length - 1]
            const baseColor = lastValue >= 0 ? '245, 108, 108' : '103, 194, 58'  // RGB for red/green
            return {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                {
                  offset: 0,
                  color: `rgba(${baseColor}, 0.3)`
                },
                {
                  offset: 1,
                  color: `rgba(${baseColor}, 0.1)`
                }
              ]
            }
          }
        },
        data: rates
      }
    ]
  }
})
</script>

<style scoped>
.return-rate-chart {
  width: 100%;
  height: 200px;
}
</style>

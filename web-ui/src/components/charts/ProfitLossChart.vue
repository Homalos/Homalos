<template>
  <div class="profit-loss-chart">
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
  const profits = props.data.map(item => item.profit)

  return {
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        const value = params[0].value
        const color = value >= 0 ? '#F56C6C' : '#67C23A'  // 红涨绿跌
        const symbol = value >= 0 ? '+' : ''
        return `${params[0].axisValue}<br/>盈亏: <span style="color: ${color}">${symbol}¥${value.toLocaleString()}</span>`
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
          return (value / 1000).toFixed(0) + 'k'
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
        name: '盈亏',
        type: 'bar',
        barWidth: '60%',
        itemStyle: {
          color: function(params) {
            return params.value >= 0 ? '#F56C6C' : '#67C23A'  // 红涨绿跌
          }
        },
        data: profits
      }
    ]
  }
})
</script>

<style scoped>
.profit-loss-chart {
  width: 100%;
  height: 200px;
}
</style>

<template>
  <div class="equity-curve-chart">
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
  const values = props.data.map(item => item.value)

  return {
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        const value = params[0].value
        return `${params[0].axisValue}<br/>权益: ¥${value.toLocaleString()}`
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
          return (value / 10000).toFixed(0) + '万'
        }
      }
    },
    series: [
      {
        name: '权益',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: {
          color: '#409EFF',
          width: 2
        },
        itemStyle: {
          color: '#409EFF'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0,
                color: 'rgba(64, 158, 255, 0.3)'
              },
              {
                offset: 1,
                color: 'rgba(64, 158, 255, 0.1)'
              }
            ]
          }
        },
        data: values
      }
    ]
  }
})
</script>

<style scoped>
.equity-curve-chart {
  width: 100%;
  height: 200px;
}
</style>

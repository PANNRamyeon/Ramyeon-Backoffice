<!-- BarChart.vue -->
<template>
  <div class="chart-wrapper" :style="{ width: 500 + 'px', height: 250 + 'px' }">
    <Bar :data="chartData" :options="options" />
  </div>
</template>

<script>
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

export default {
  name: 'BarChart',
  components: { Bar },
  props: {
    chartData: {
      type: Object,
      required: true
    },
    selectedFrequency: {
      type: String,
      default: 'monthly'
    },
    width: {
      type: Number,
      default: 600
    },
    height: {
      type: Number,
      default: 400
    }
  },
  computed: {
    options() {
      return {
        responsive: true,
        maintainAspectRatio: false,  
        plugins: {
          title: {
            display: false,
            text: `Sales by Category (${this.selectedFrequency})`
          },
          legend: {
            display: false,
          }
        },
        scales: {
          y: {
            beginAtZero: true
          }
        }
      }
    }
  }
}
</script>

<style scoped>
.chart-wrapper {
  position: relative;
}
</style>
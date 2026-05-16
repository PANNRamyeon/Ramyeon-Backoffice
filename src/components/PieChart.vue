    <template>
      <Pie :data="chartData" :options="chartOptions" />
    </template>

    <script>
    import { Pie } from 'vue-chartjs';
    import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

    // Register the necessary Chart.js elements for a pie chart
    ChartJS.register(ArcElement, Tooltip, Legend);

    export default {
      name: 'PieChart',
      components: { Pie },
      props: {
        chartData: {
          type: Object,
          required: true,
        },
        chartOptions: {
          type: Object,
          default: () => ({
            responsive: true,
            maintainAspectRatio: false,
          }),
        },
      },
    };
    </script>
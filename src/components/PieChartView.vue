    <template>
      <PieChart :chartData="myPieChartData" :chartOptions="myPieChartOptions" />
    </template>

    <script>
    import PieChart from './PieChart.vue'; // Adjust path as needed

    export default {
      components: { PieChart },
      data() {
        return {
          myPieChartData: {
            labels: ['Red', 'Blue', 'Yellow'],
            datasets: [
              {
                data: [300, 50, 100],
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56'],
                hoverOffset: 4, // Optional: adds a slight offset on hover
              },
            ],
          },
          myPieChartOptions: {
            responsive: true,
            maintainAspectRatio: false,
            // Add other Chart.js options as needed, e.g., plugins for title, etc.
          },
        };
      },
    };
    </script>
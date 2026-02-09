<template>
  <div v-if="isVisible" class="modal fade show" tabindex="-1" style="display:block;" @click.self="close">
    <div class="modal-dialog modal-lg modal-dialog-scrollable">
      <div class="modal-content p-4">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h5 class="modal-title text-primary">Batch Details: {{ batch?.batch_number }}</h5>
          <button type="button" class="btn-close" @click="close"></button>
        </div>

        <div v-if="batch" class="mb-3">
          <table class="table table-sm">
            <tbody>
              <tr><th>Batch Number</th><td>{{ batch.batch_number }}</td></tr>
              <tr><th>Status</th><td>{{ batch.status }}</td></tr>
              <tr><th>Quantity Received</th><td>{{ batch.quantity_received }}</td></tr>
              <tr><th>Remaining</th><td>{{ batch.quantity_remaining }}</td></tr>
              <tr><th>Cost Price</th><td>₱{{ batch.cost_price }}</td></tr>
              <tr><th>Supplier ID</th><td>{{ batch.supplier_id || 'N/A' }}</td></tr>
              <tr><th>Received On</th><td>{{ formatDate(batch.date_received) }}</td></tr>
              <tr><th>Expiry Date</th><td>{{ formatDate(batch.expiry_date) }}</td></tr>
            </tbody>
          </table>

          <div v-if="batch.usage_history?.length">
            <h6 class="mt-4">Usage History</h6>
            <table class="table table-striped table-sm">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Qty Used</th>
                  <th>Remaining</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(u, idx) in batch.usage_history" :key="idx">
                  <td>{{ formatDate(u.timestamp) }}</td>
                  <td>{{ u.adjustment_type }}</td>
                  <td>{{ u.quantity_used }}</td>
                  <td>{{ u.remaining_after }}</td>
                  <td>{{ u.notes }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="text-end mt-3">
          <button class="btn btn-secondary" @click="close">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'BatchDetailsModal',
  setup() {
    const isVisible = ref(false)
    const batch = ref(null)

    const open = (data) => {
      batch.value = data
      isVisible.value = true
    }

    const close = () => {
      isVisible.value = false
      batch.value = null
    }

    const formatDate = (dateString) => {
      if (!dateString) return 'N/A'
      return new Date(dateString).toLocaleString()
    }

    return { isVisible, batch, open, close, formatDate }
  }
}
</script>

<style scoped>
.modal {
  background: rgba(0, 0, 0, 0.5);
}
</style>

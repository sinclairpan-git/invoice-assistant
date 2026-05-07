<template>
  <div class="responsive-table">
    <table>
      <thead>
        <tr>
          <th>批次</th>
          <th>阶段</th>
          <th>文件统计</th>
          <th>建议通过</th>
          <th class="right">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="batch in batches" :key="batch.id">
          <td>
            <strong>{{ batch.batch_no }}</strong>
            <span class="table-subtext">{{ batch.created_by }}</span>
          </td>
          <td>
            <AppStatusTag
              :label="batch.progress?.stage_text || getStatusLabel(batch.status)"
              :severity="getStatusSeverity(batch.status)"
            />
            <AppProgress :value="batch.progress?.progress_percent ?? 0" :show-value="false" />
          </td>
          <td>总数 {{ batch.total_files }}<span class="table-subtext">完成 {{ batch.completed_files }} / 失败 {{ batch.failed_files }}</span></td>
          <td>数量 {{ batch.suggested_pass_count }}<span class="table-subtext">金额 {{ batch.suggested_pass_total_amount }}</span></td>
          <td class="right"><AppButton label="查看结果" variant="ghost" @click="$emit('openResults', batch.id)" /></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { Batch } from "../../app/types";
import { getStatusLabel, getStatusSeverity } from "../../domain/presentation";
import AppButton from "../../ui-adapter/AppButton.vue";
import AppProgress from "../../ui-adapter/AppProgress.vue";
import AppStatusTag from "../../ui-adapter/AppStatusTag.vue";

defineProps<{
  batches: Batch[];
}>();

defineEmits<{
  openResults: [batchId: string];
}>();
</script>

<template>
  <div class="data">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据同步</span>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-click="handleTabClick">
        <!-- 单只股票同步 -->
        <el-tab-pane label="单只股票" name="single">
          <el-form :model="singleForm" label-width="100px">
            <el-form-item label="股票代码">
              <el-input
                v-model="singleForm.code"
                placeholder="例如: 000001.SZ"
                style="width: 200px"
              />
            </el-form-item>
            <el-form-item label="同步天数">
              <el-input-number
                v-model="singleForm.days"
                :min="1"
                :max="3650"
                style="width: 200px"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="syncing"
                @click="syncSingleStock"
              >
                {{ syncing ? "同步中..." : "开始同步" }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 批量同步 -->
        <el-tab-pane label="批量同步" name="batch">
          <el-form :model="batchForm" label-width="100px">
            <el-form-item label="股票代码">
              <el-input
                v-model="batchForm.codes"
                type="textarea"
                :rows="4"
                placeholder="输入股票代码，每行一个，例如:&#10;000001.SZ&#10;000002.SZ&#10;600000.SH"
                style="width: 400px"
              />
            </el-form-item>
            <el-form-item label="同步天数">
              <el-input-number
                v-model="batchForm.days"
                :min="1"
                :max="3650"
                style="width: 200px"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="batchSyncing"
                @click="syncBatchStocks"
              >
                {{ batchSyncing ? "同步中..." : "批量同步" }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 同步历史 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <span>同步历史</span>
      </template>
      <el-table :data="syncHistory" stripe>
        <el-table-column prop="type" label="类型" width="100" />
        <el-table-column prop="code" label="股票代码" />
        <el-table-column prop="days" label="天数" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
              {{ row.status === "success" ? "成功" : "失败" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" />
        <el-table-column prop="timestamp" label="时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { ElMessage } from "element-plus";
import { dataApi } from "@/api";

const activeTab = ref("single");

const singleForm = reactive({
  code: "",
  days: 365,
});

const batchForm = reactive({
  codes: "",
  days: 365,
});

const syncing = ref(false);
const batchSyncing = ref(false);

interface SyncRecord {
  type: string;
  code: string;
  days: number;
  status: "success" | "error";
  message: string;
  timestamp: string;
}

const syncHistory = ref<SyncRecord[]>([]);

const addSyncRecord = (record: SyncRecord) => {
  syncHistory.value.unshift(record);
  if (syncHistory.value.length > 50) {
    syncHistory.value = syncHistory.value.slice(0, 50);
  }
};

const syncSingleStock = async () => {
  if (!singleForm.code.trim()) {
    ElMessage.warning("请输入股票代码");
    return;
  }

  syncing.value = true;
  try {
    const response = await dataApi.syncStock(singleForm.code, singleForm.days);
    ElMessage.success("数据同步成功");
    addSyncRecord({
      type: "单只",
      code: singleForm.code,
      days: singleForm.days,
      status: "success",
      message: response.message || "同步完成",
      timestamp: new Date().toLocaleString(),
    });
  } catch (error: any) {
    ElMessage.error("数据同步失败");
    addSyncRecord({
      type: "单只",
      code: singleForm.code,
      days: singleForm.days,
      status: "error",
      message: error.response?.data?.detail || error.message,
      timestamp: new Date().toLocaleString(),
    });
  } finally {
    syncing.value = false;
  }
};

const syncBatchStocks = async () => {
  const codes = batchForm.codes
    .split("\n")
    .map((code) => code.trim())
    .filter((code) => code.length > 0);

  if (codes.length === 0) {
    ElMessage.warning("请输入至少一个股票代码");
    return;
  }

  batchSyncing.value = true;
  try {
    const response = await dataApi.syncBatch(codes, batchForm.days);
    ElMessage.success(`批量同步完成，共处理 ${codes.length} 只股票`);
    addSyncRecord({
      type: "批量",
      code: codes.join(", "),
      days: batchForm.days,
      status: "success",
      message: `处理 ${codes.length} 只股票`,
      timestamp: new Date().toLocaleString(),
    });
  } catch (error: any) {
    ElMessage.error("批量同步失败");
    addSyncRecord({
      type: "批量",
      code: codes.slice(0, 3).join(", ") + (codes.length > 3 ? "..." : ""),
      days: batchForm.days,
      status: "error",
      message: error.response?.data?.detail || error.message,
      timestamp: new Date().toLocaleString(),
    });
  } finally {
    batchSyncing.value = false;
  }
};

const handleTabClick = () => {
  // 可以在这里添加标签切换逻辑
};
</script>

<style scoped>
.data {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

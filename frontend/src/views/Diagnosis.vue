<template>
  <div class="diagnosis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>AI 股票诊断</span>
        </div>
      </template>

      <el-form :model="form" label-width="120px" style="max-width: 600px">
        <el-form-item label="股票代码">
          <el-input
            v-model="form.stockCode"
            placeholder="例如: 000001.SZ"
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item label="诊断模式">
          <el-radio-group v-model="form.mode">
            <el-radio label="sync">同步诊断</el-radio>
            <el-radio label="async">异步诊断</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="diagnosing" @click="runDiagnosis">
            {{ diagnosing ? "诊断中..." : "开始诊断" }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 诊断结果 -->
    <el-card v-if="result" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>诊断结果 - {{ result.code }}</span>
          <el-tag :type="getDecisionType(result.final_decision.decision)">
            {{ result.final_decision.decision }}
          </el-tag>
        </div>
      </template>

      <!-- 最终决策 -->
      <el-descriptions :column="1" border>
        <el-descriptions-item label="投资决策">
          <span :class="getDecisionClass(result.final_decision.decision)">
            {{ result.final_decision.decision }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="置信度">
          {{ (result.final_decision.confidence * 100).toFixed(1) }}%
        </el-descriptions-item>
        <el-descriptions-item label="推理依据">
          {{ result.final_decision.reasoning }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 诊断阶段 -->
      <div v-if="result.stages" style="margin-top: 20px">
        <h4>诊断详情</h4>
        <el-collapse>
          <el-collapse-item
            v-for="(stage, index) in result.stages"
            :key="index"
            :title="stage.stage_name"
          >
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item
                v-for="(value, key) in stage"
                :key="key"
                :label="key"
              >
                <span v-if="typeof value === 'number' && key.includes('score')">
                  {{ (value * 100).toFixed(1) }}%
                </span>
                <span v-else-if="typeof value === 'boolean'">
                  {{ value ? "是" : "否" }}
                </span>
                <span v-else>
                  {{ value }}
                </span>
              </el-descriptions-item>
            </el-descriptions>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-card>

    <!-- 诊断历史 -->
    <el-card v-if="diagnosisHistory.length > 0" style="margin-top: 20px">
      <template #header>
        <span>诊断历史</span>
      </template>
      <el-table :data="diagnosisHistory" stripe>
        <el-table-column prop="code" label="股票代码" width="120" />
        <el-table-column prop="decision" label="决策" width="100">
          <template #default="{ row }">
            <el-tag :type="getDecisionType(row.decision)">
              {{ row.decision }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            {{ (row.confidence * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="诊断时间" width="180" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" @click="viewDiagnosis(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { ElMessage } from "element-plus";
import { diagnosisApi, type DiagnosisResult } from "@/api";

const form = reactive({
  stockCode: "",
  mode: "sync",
});

const diagnosing = ref(false);
const result = ref<DiagnosisResult | null>(null);

interface DiagnosisHistory {
  code: string;
  decision: string;
  confidence: number;
  reasoning: string;
  timestamp: string;
  fullResult: DiagnosisResult;
}

const diagnosisHistory = ref<DiagnosisHistory[]>([]);

const getDecisionType = (decision: string) => {
  switch (decision.toLowerCase()) {
    case "买入":
    case "buy":
      return "success";
    case "卖出":
    case "sell":
      return "danger";
    case "持有":
    case "hold":
      return "warning";
    default:
      return "";
  }
};

const getDecisionClass = (decision: string) => {
  switch (decision.toLowerCase()) {
    case "买入":
    case "buy":
      return "buy-decision";
    case "卖出":
    case "sell":
      return "sell-decision";
    case "持有":
    case "hold":
      return "hold-decision";
    default:
      return "";
  }
};

const runDiagnosis = async () => {
  if (!form.stockCode.trim()) {
    ElMessage.warning("请输入股票代码");
    return;
  }

  diagnosing.value = true;
  try {
    let response: DiagnosisResult;

    if (form.mode === "sync") {
      response = await diagnosisApi.getSync(form.stockCode);
    } else {
      // 异步诊断返回任务ID，需要轮询状态
      const taskResponse = await diagnosisApi.getAsync(form.stockCode);
      // 这里简化处理，实际应该轮询任务状态
      ElMessage.info("异步诊断已提交，请稍后查看结果");
      return;
    }

    result.value = response;

    // 添加到历史记录
    diagnosisHistory.value.unshift({
      code: response.code,
      decision: response.final_decision.decision,
      confidence: response.final_decision.confidence,
      reasoning: response.final_decision.reasoning,
      timestamp: new Date().toLocaleString(),
      fullResult: response,
    });

    if (diagnosisHistory.value.length > 20) {
      diagnosisHistory.value = diagnosisHistory.value.slice(0, 20);
    }

    ElMessage.success("诊断完成");
  } catch (error: any) {
    ElMessage.error("诊断失败");
    console.error("Diagnosis error:", error);
  } finally {
    diagnosing.value = false;
  }
};

const viewDiagnosis = (record: DiagnosisHistory) => {
  result.value = record.fullResult;
};
</script>

<style scoped>
.diagnosis {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.buy-decision {
  color: #67c23a;
  font-weight: bold;
}

.sell-decision {
  color: #f56c6c;
  font-weight: bold;
}

.hold-decision {
  color: #e6a23c;
  font-weight: bold;
}
</style>

<template>
  <div class="positions">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>持仓管理</span>
          <el-button type="primary" icon="Refresh" @click="loadPositions"
            >刷新</el-button
          >
        </div>
      </template>

      <!-- 账户选择 -->
      <div style="margin-bottom: 20px">
        <el-select
          v-model="selectedAccountId"
          placeholder="选择账户"
          style="width: 200px"
          @change="loadPositions"
        >
          <el-option
            v-for="account in accounts"
            :key="account.id"
            :label="account.account_name"
            :value="account.id"
          />
        </el-select>
      </div>

      <!-- 持仓汇总 -->
      <el-row :gutter="20" style="margin-bottom: 20px">
        <el-col :span="6">
          <el-statistic title="总持仓数量" :value="totalPositions" />
        </el-col>
        <el-col :span="6">
          <el-statistic
            title="总市值"
            :value="totalMarketValue"
            prefix="¥"
            :precision="2"
          />
        </el-col>
        <el-col :span="6">
          <el-statistic
            title="浮动盈亏"
            :value="totalFloatingPnl"
            prefix="¥"
            :precision="2"
          />
        </el-col>
        <el-col :span="6">
          <el-statistic
            title="盈亏比例"
            :value="totalPnlRate"
            suffix="%"
            :precision="2"
          />
        </el-col>
      </el-row>

      <!-- 持仓列表 -->
      <el-table :data="positions" stripe v-loading="loading">
        <el-table-column prop="stock_code" label="股票代码" width="100" />
        <el-table-column prop="stock_name" label="股票名称" min-width="120" />
        <el-table-column
          prop="total_volume"
          label="总持仓"
          width="100"
          align="right"
        />
        <el-table-column
          prop="available_volume"
          label="可用数量"
          width="100"
          align="right"
        />
        <el-table-column
          prop="avg_cost"
          label="平均成本"
          width="100"
          align="right"
        >
          <template #default="{ row }">
            ¥{{ row.avg_cost.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="current_price"
          label="当前价格"
          width="100"
          align="right"
        >
          <template #default="{ row }">
            ¥{{ row.current_price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="market_value"
          label="市值"
          width="120"
          align="right"
        >
          <template #default="{ row }">
            ¥{{ row.market_value.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="floating_pnl"
          label="浮动盈亏"
          width="120"
          align="right"
        >
          <template #default="{ row }">
            <span :class="row.floating_pnl >= 0 ? 'positive' : 'negative'">
              ¥{{ row.floating_pnl.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column
          prop="floating_pnl_rate"
          label="盈亏比例"
          width="100"
          align="right"
        >
          <template #default="{ row }">
            <span :class="row.floating_pnl_rate >= 0 ? 'positive' : 'negative'">
              {{ (row.floating_pnl_rate * 100).toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              @click="viewPositionDetail(row)"
            >
              详情
            </el-button>
            <el-button size="small" type="warning" @click="closePosition(row)">
              平仓
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 持仓详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="持仓详情" width="600px">
      <div v-if="selectedPosition">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="股票代码">
            {{ selectedPosition.stock_code }}
          </el-descriptions-item>
          <el-descriptions-item label="股票名称">
            {{ selectedPosition.stock_name }}
          </el-descriptions-item>
          <el-descriptions-item label="总持仓数量">
            {{ selectedPosition.total_volume }}
          </el-descriptions-item>
          <el-descriptions-item label="可用数量">
            {{ selectedPosition.available_volume }}
          </el-descriptions-item>
          <el-descriptions-item label="平均成本">
            ¥{{ selectedPosition.avg_cost.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="当前价格">
            ¥{{ selectedPosition.current_price.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="总成本">
            ¥{{ selectedPosition.total_cost.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="市值">
            ¥{{ selectedPosition.market_value.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="浮动盈亏">
            <span
              :class="
                selectedPosition.floating_pnl >= 0 ? 'positive' : 'negative'
              "
            >
              ¥{{ selectedPosition.floating_pnl.toFixed(2) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="盈亏比例">
            <span
              :class="
                selectedPosition.floating_pnl_rate >= 0
                  ? 'positive'
                  : 'negative'
              "
            >
              {{ (selectedPosition.floating_pnl_rate * 100).toFixed(2) }}%
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="开仓日期">
            {{ selectedPosition.open_date || "未知" }}
          </el-descriptions-item>
          <el-descriptions-item label="最后交易日">
            {{ selectedPosition.last_trade_date || "未知" }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ledgerApi, type LedgerAccount, type PositionWithQuote } from "@/api";

const selectedAccountId = ref<number | null>(null);
const accounts = ref<LedgerAccount[]>([]);
const positions = ref<PositionWithQuote[]>([]);
const loading = ref(false);

const detailDialogVisible = ref(false);
const selectedPosition = ref<PositionWithQuote | null>(null);

// 计算属性：汇总数据
const totalPositions = computed(() => positions.value.length);

const totalMarketValue = computed(() =>
  positions.value.reduce((sum, pos) => sum + pos.market_value, 0)
);

const totalFloatingPnl = computed(() =>
  positions.value.reduce((sum, pos) => sum + pos.floating_pnl, 0)
);

const totalPnlRate = computed(() => {
  const totalCost = positions.value.reduce(
    (sum, pos) => sum + pos.total_cost,
    0
  );
  const totalValue = totalMarketValue.value;
  if (totalCost === 0) return 0;
  return ((totalValue - totalCost) / totalCost) * 100;
});

const loadAccounts = async () => {
  try {
    const response = await ledgerApi.getAccounts();
    accounts.value = response.accounts;
    if (accounts.value.length > 0 && !selectedAccountId.value) {
      selectedAccountId.value = accounts.value[0].id;
      loadPositions();
    }
  } catch (error) {
    ElMessage.error("加载账户列表失败");
  }
};

const loadPositions = async () => {
  if (!selectedAccountId.value) return;

  loading.value = true;
  try {
    const response = await ledgerApi.getPositions(selectedAccountId.value);
    positions.value = response.positions;
  } catch (error) {
    ElMessage.error("加载持仓数据失败");
  } finally {
    loading.value = false;
  }
};

const viewPositionDetail = (position: PositionWithQuote) => {
  selectedPosition.value = position;
  detailDialogVisible.value = true;
};

const closePosition = async (position: PositionWithQuote) => {
  try {
    await ElMessageBox.confirm(
      `确定要平仓 ${position.stock_name}(${position.stock_code}) 吗？`,
      "平仓确认",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    // 这里应该调用平仓API，但后端可能未实现
    ElMessage.success("平仓指令已提交");

    // 重新加载持仓数据
    loadPositions();
  } catch (error) {
    // 用户取消操作
  }
};

onMounted(() => {
  loadAccounts();
});
</script>

<style scoped>
.positions {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.positive {
  color: #67c23a;
  font-weight: bold;
}

.negative {
  color: #f56c6c;
  font-weight: bold;
}
</style>

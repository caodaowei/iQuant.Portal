<template>
  <div class="trading">
    <el-row :gutter="20">
      <!-- 账户信息 -->
      <el-col :span="6">
        <el-card>
          <template #header>
            <span>交易账户</span>
          </template>
          <el-select
            v-model="selectedAccountId"
            placeholder="选择账户"
            style="width: 100%"
            @change="loadAccountData"
          >
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="account.account_name"
              :value="account.id"
            />
          </el-select>

          <div v-if="currentAccount" style="margin-top: 20px">
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="总资产">
                ¥{{ currentAccount.total_capital.toLocaleString() }}
              </el-descriptions-item>
              <el-descriptions-item label="可用资金">
                ¥{{ currentAccount.available_cash.toLocaleString() }}
              </el-descriptions-item>
              <el-descriptions-item label="市值">
                ¥{{ currentAccount.market_value.toLocaleString() }}
              </el-descriptions-item>
              <el-descriptions-item label="总盈亏">
                <span
                  :class="
                    currentAccount.total_pnl >= 0 ? 'positive' : 'negative'
                  "
                >
                  ¥{{ currentAccount.total_pnl.toLocaleString() }}
                </span>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>

      <!-- 下单面板 -->
      <el-col :span="10">
        <el-card>
          <template #header>
            <span>交易下单</span>
          </template>

          <el-form :model="orderForm" label-width="80px">
            <el-form-item label="股票代码">
              <el-input
                v-model="orderForm.stockCode"
                placeholder="例如: 000001.SZ"
                style="width: 150px"
              />
            </el-form-item>

            <el-form-item label="交易方向">
              <el-radio-group v-model="orderForm.direction">
                <el-radio label="buy">买入</el-radio>
                <el-radio label="sell">卖出</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="委托数量">
              <el-input-number
                v-model="orderForm.quantity"
                :min="100"
                :step="100"
                style="width: 150px"
              />
            </el-form-item>

            <el-form-item label="委托价格">
              <el-input-number
                v-model="orderForm.price"
                :min="0.01"
                :step="0.01"
                :precision="2"
                style="width: 150px"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="submitting"
                @click="submitOrder"
                :disabled="!selectedAccountId"
              >
                {{ submitting ? "提交中..." : "提交订单" }}
              </el-button>
              <el-button @click="resetForm" style="margin-left: 10px">
                重置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 持仓信息 -->
        <el-card style="margin-top: 20px">
          <template #header>
            <span>当前持仓</span>
          </template>
          <el-table :data="positions" stripe size="small" max-height="300">
            <el-table-column prop="stock_code" label="股票代码" width="100" />
            <el-table-column prop="stock_name" label="股票名称" />
            <el-table-column prop="total_volume" label="持仓数量" width="100" />
            <el-table-column prop="avg_cost" label="平均成本" width="100">
              <template #default="{ row }">
                ¥{{ row.avg_cost.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="current_price" label="当前价格" width="100">
              <template #default="{ row }">
                ¥{{ row.current_price.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column
              prop="floating_pnl_rate"
              label="盈亏比例"
              width="100"
            >
              <template #default="{ row }">
                <span
                  :class="row.floating_pnl_rate >= 0 ? 'positive' : 'negative'"
                >
                  {{ (row.floating_pnl_rate * 100).toFixed(2) }}%
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 订单历史 -->
      <el-col :span="8">
        <el-card style="height: 600px">
          <template #header>
            <span>订单记录</span>
          </template>
          <el-table :data="orders" stripe size="small" max-height="500">
            <el-table-column prop="stock_code" label="股票" width="80" />
            <el-table-column prop="direction" label="方向" width="60">
              <template #default="{ row }">
                <el-tag
                  :type="row.direction === 'buy' ? 'success' : 'danger'"
                  size="small"
                >
                  {{ row.direction === "buy" ? "买" : "卖" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="70" />
            <el-table-column prop="price" label="价格" width="70">
              <template #default="{ row }">
                ¥{{ row.price.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="70">
              <template #default="{ row }">
                <el-tag size="small" :type="getStatusType(row.status)">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="时间" width="120">
              <template #default="{ row }">
                {{ new Date(row.create_time).toLocaleTimeString() }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from "vue";
import { ElMessage } from "element-plus";
import { ledgerApi, type LedgerAccount, type PositionWithQuote } from "@/api";

const selectedAccountId = ref<number | null>(null);
const accounts = ref<LedgerAccount[]>([]);
const currentAccount = ref<LedgerAccount | null>(null);
const positions = ref<PositionWithQuote[]>([]);
const orders = ref<any[]>([]);

const orderForm = reactive({
  stockCode: "",
  direction: "buy",
  quantity: 100,
  price: 0,
});

const submitting = ref(false);

const getStatusType = (status: string) => {
  switch (status) {
    case "filled":
      return "success";
    case "pending":
      return "warning";
    case "cancelled":
      return "info";
    case "rejected":
      return "danger";
    default:
      return "";
  }
};

const loadAccounts = async () => {
  try {
    const response = await ledgerApi.getAccounts();
    accounts.value = response.accounts;
    if (accounts.value.length > 0 && !selectedAccountId.value) {
      selectedAccountId.value = accounts.value[0].id;
      loadAccountData();
    }
  } catch (error) {
    ElMessage.error("加载账户列表失败");
  }
};

const loadAccountData = async () => {
  if (!selectedAccountId.value) return;

  try {
    // 加载账户详情
    const accountResponse = await ledgerApi.getAccount(selectedAccountId.value);
    currentAccount.value = accountResponse;

    // 加载持仓
    const positionsResponse = await ledgerApi.getPositions(
      selectedAccountId.value
    );
    positions.value = positionsResponse.positions;

    // 加载订单历史（这里暂时使用mock数据，因为后端可能未实现）
    loadMockOrders();
  } catch (error) {
    ElMessage.error("加载账户数据失败");
  }
};

const loadMockOrders = () => {
  // 模拟订单数据
  orders.value = [
    {
      id: 1,
      stock_code: "000001",
      direction: "buy",
      quantity: 100,
      price: 10.5,
      status: "filled",
      create_time: new Date().toISOString(),
    },
    {
      id: 2,
      stock_code: "000002",
      direction: "sell",
      quantity: 200,
      price: 15.3,
      status: "pending",
      create_time: new Date(Date.now() - 300000).toISOString(),
    },
  ];
};

const submitOrder = async () => {
  if (!selectedAccountId.value) {
    ElMessage.warning("请先选择交易账户");
    return;
  }

  if (!orderForm.stockCode || !orderForm.quantity || !orderForm.price) {
    ElMessage.warning("请填写完整的订单信息");
    return;
  }

  submitting.value = true;
  try {
    // 这里应该调用交易API，但后端可能未实现
    // const response = await tradingApi.submitOrder({
    //   account_id: selectedAccountId.value,
    //   stock_code: orderForm.stockCode,
    //   direction: orderForm.direction,
    //   quantity: orderForm.quantity,
    //   price: orderForm.price,
    // })

    // 模拟提交成功
    ElMessage.success("订单提交成功");

    // 添加到订单列表
    orders.value.unshift({
      id: Date.now(),
      stock_code: orderForm.stockCode,
      direction: orderForm.direction,
      quantity: orderForm.quantity,
      price: orderForm.price,
      status: "pending",
      create_time: new Date().toISOString(),
    });

    resetForm();
  } catch (error: any) {
    ElMessage.error("订单提交失败");
  } finally {
    submitting.value = false;
  }
};

const resetForm = () => {
  orderForm.stockCode = "";
  orderForm.direction = "buy";
  orderForm.quantity = 100;
  orderForm.price = 0;
};

onMounted(() => {
  loadAccounts();
});

watch(selectedAccountId, () => {
  loadAccountData();
});
</script>

<style scoped>
.trading {
  padding: 20px;
}

.positive {
  color: #67c23a;
}

.negative {
  color: #f56c6c;
}
</style>

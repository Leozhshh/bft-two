{
  // 因子报告输出间隔（秒）
  // 例如：10 = 每 10 秒输出一次因子状态（用于调试/监控）
  "factor_report_interval": 10,

  // ATR 仓位风险系数（每笔交易愿意承担的风险比例）
  // 例如：0.01 = 账户余额的 1%
  // 用于 ATR 动态仓位模型：
  //   风险预算 = balance × risk_factor
  //   qty = 风险预算 / ATR
  "risk_factor": 0.01,

  // 最大仓位占用比例（用于限制仓位价值）
  // 最大仓位价值 = balance × leverage × max_position_ratio
  // 例如：
  //   balance = 5000
  //   leverage = 10
  //   max_position_ratio = 0.5
  //   → 最大仓位价值 = 5000 × 10 × 0.5 = 25000 USDT
  "max_position_ratio": 0.5,

  // 默认杠杆（用于计算最大仓位限制）
  // 注意：这是“仓位管理用的杠杆”，不是交易所实际杠杆
  // 例如：10 = 10x
  "default_leverage": 20
}
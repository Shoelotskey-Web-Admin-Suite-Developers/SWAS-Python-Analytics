import { Branch } from "../models/Branch"

/**
 * Generate a unique payment id of the form `PAY-[increment]-[branch_code]`.
 * It reads the highest existing payment_id for the branch and increments the numeric suffix.
 */
export async function generatePaymentId(branch_code: string) {
  // Find the max numeric suffix for existing payments for this branch.
  // Payment model lives in ../models/payments but importing it here would create a cycle with controllers
  // so we'll require it lazily.
  const Payment = require("../models/payments").Payment

  // Escape branch code for regex
  const escapedBranch = String(branch_code || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const re = new RegExp(`^PAY-(\\d+)-${escapedBranch}$`)

  // find one payment matching the branch code and with the highest numeric increment
  const latest = await Payment.find({ payment_id: { $regex: re } })
    .sort({ _id: -1 })
    .limit(100)

  let maxNum = 0
  for (const p of latest) {
    const m = (p.payment_id || "").match(re)
    if (m && m[1]) {
      const n = parseInt(m[1], 10)
      if (!isNaN(n) && n > maxNum) maxNum = n
    }
  }

  const next = maxNum + 1
  return `PAY-${next}-${branch_code}`
}

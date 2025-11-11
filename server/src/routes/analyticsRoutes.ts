import express from "express"
import { getDailyRevenue, getForecast, getMonthlyRevenue, getTopServices, getSalesBreakdown } from "../controllers/analyticsController"

const router = express.Router()

router.get("/daily-revenue", getDailyRevenue)
router.get("/forecast", getForecast)
router.get("/monthly-revenue", getMonthlyRevenue)
router.get("/top-services", getTopServices)
router.get("/sales-breakdown", getSalesBreakdown)

export default router

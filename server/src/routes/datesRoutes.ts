import express from "express";
import { upsertDatesByLineItemId, getDatesByLineItemId, deleteDatesByLineItemId } from "../controllers/datesController";

const router = express.Router();

// GET /api/dates/:line_item_id
router.get("/:line_item_id", getDatesByLineItemId);

// PUT /api/dates
router.put("/", upsertDatesByLineItemId);

// DELETE /api/dates/:line_item_id
router.delete("/:line_item_id", deleteDatesByLineItemId); // Add this route

export default router;
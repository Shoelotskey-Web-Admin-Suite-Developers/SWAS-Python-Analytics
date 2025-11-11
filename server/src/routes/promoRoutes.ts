import { Router } from "express";
import {
  createPromo,
  getAllPromos,
  updatePromo,
  deletePromo,
} from "../controllers/promoController";

const router = Router();

// Create promo
router.post("/", createPromo);

// Get promos by branch_id (query param)
router.get("/", getAllPromos);

// Update promo by ID (promo_id in params)
router.put("/:id", updatePromo);

// Delete promo by ID (promo_id in params)
router.delete("/:id", deletePromo);

export default router;

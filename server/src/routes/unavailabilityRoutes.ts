/// src/routes/unavailabilityRoutes.ts
import express from "express";
import {
  addUnavailability,
  getAllUnavailability,
  getUnavailabilityById,
  deleteUnavailability,
} from "../controllers/unavailabilityController";

const router = express.Router();

// Create a new unavailability
router.post("/", addUnavailability);

// Get all unavailability records
router.get("/", getAllUnavailability);

// Get a specific unavailability by unavailability_id
router.get("/:id", getUnavailabilityById);

// Delete a specific unavailability by unavailability_id
router.delete("/:id", deleteUnavailability);

export default router;

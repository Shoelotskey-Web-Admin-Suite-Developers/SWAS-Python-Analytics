import express from "express";
import {
  getApprovedAppointments,
  getPendingAppointments,
  cancelAffectedAppointmentsController,
  updateAppointmentStatus,
} from "../controllers/appointmentsController";

const router = express.Router();

router.get("/approved", getApprovedAppointments);
router.get("/pending", getPendingAppointments);

// Use the controller wrapper for cancelling affected appointments
router.post("/cancel-affected", cancelAffectedAppointmentsController);

// Update single appointment status by appointment_id
router.put("/:appointment_id/status", updateAppointmentStatus);

export default router;

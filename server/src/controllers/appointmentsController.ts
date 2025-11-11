// src/controllers/appointmentsController.ts
import { Request, Response } from "express";
import { Appointment, IAppointment } from "../models/Appointments";
import { IUnavailability } from "../models/Unavailability";
import { cancelAffectedAppointments as cancelAppointmentsService } from "../controllers/appointmentsService";
import { sendPushNotification } from "../utils/pushNotifications";

// Get all approved appointments
export const getApprovedAppointments = async (req: Request, res: Response) => {
  try {
    const approvedAppointments: IAppointment[] = await Appointment.find({
      status: "Approved",
    }).sort({ date_for_inquiry: 1, time_start: 1 });

    return res.status(200).json({ success: true, data: approvedAppointments });
  } catch (error) {
    console.error("Error fetching approved appointments:", error);
    return res.status(500).json({ success: false, message: "Server error" });
  }
};

// Get all pending appointments
export const getPendingAppointments = async (req: Request, res: Response) => {
  try {
    const pendingAppointments: IAppointment[] = await Appointment.find({
      status: "Pending",
    }).sort({ date_for_inquiry: 1, time_start: 1 });

    return res.status(200).json({ success: true, data: pendingAppointments });
  } catch (error) {
    console.error("Error fetching pending appointments:", error);
    return res.status(500).json({ success: false, message: "Server error" });
  }
};

// Controller wrapper for cancelling affected appointments
export const cancelAffectedAppointmentsController = async (req: Request, res: Response) => {
  try {
    const unavailability: IUnavailability = req.body; // expect JSON with date_unavailable, type, time_start?, time_end?
    await cancelAppointmentsService(unavailability);

    return res.status(200).json({
      success: true,
      message: `Cancelled appointments affected by unavailability on ${unavailability.date_unavailable}`,
    });
  } catch (error) {
    console.error("Error cancelling affected appointments:", error);
    return res.status(500).json({ success: false, message: "Server error" });
  }
};

// Update appointment status (approve/cancel) with push notification
export const updateAppointmentStatus = async (req: Request, res: Response) => {
  try {
    const { appointment_id } = req.params;
    const { status } = req.body as { status?: string };

    if (!appointment_id) {
      return res.status(400).json({ success: false, message: "appointment_id is required" });
    }

    // Accept either spelling for incoming requests for backward compatibility
    const allowedStatuses = ["Pending", "Canceled", "Cancelled", "Approved"];
    if (!status || !allowedStatuses.includes(status)) {
      return res.status(400).json({ success: false, message: "Invalid or missing status" });
    }

    // Normalize stored status to American spelling 'Canceled' when a cancellation is requested
    const normalizedStatus = status === 'Cancelled' ? 'Canceled' : status;

    const updated: IAppointment | null = await Appointment.findOneAndUpdate(
      { appointment_id },
      { $set: { status: normalizedStatus } },
      { new: true }
    );

    if (!updated) {
      return res.status(404).json({ success: false, message: "Appointment not found" });
    }

    // Send push notification to customer after successful status update
    if (updated.cust_id && updated.date_for_inquiry) {
      try {
        const appointmentDate = new Date(updated.date_for_inquiry).toLocaleDateString('en-US', {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        });

        let notificationTitle = '';
        let notificationBody = '';

        if (status === 'Approved') {
          notificationTitle = 'Appointment Acknowledged';
          notificationBody = `Your appointment on ${appointmentDate} has been acknowledged.`;
        } else if (normalizedStatus === 'Canceled') {
          // Display title/body with the more common 'Canceled' phrasing but keep message readable
          notificationTitle = 'Appointment Canceled';
          notificationBody = `Your appointment on ${appointmentDate} has been canceled.`;
        }

        if (notificationTitle && notificationBody) {
          const notificationData = {
            appointmentId: updated.appointment_id,
            status: status,
            date: updated.date_for_inquiry,
            timeStart: updated.time_start,
            timeEnd: updated.time_end
          };

          // Send push notification (non-blocking)
          const pushResult = await sendPushNotification(
            updated.cust_id,
            notificationTitle,
            notificationBody,
            notificationData
          );

          if (!pushResult.success) {
            // Log push notification failure but don't fail the request
            console.warn(`Push notification failed for appointment ${appointment_id}:`, pushResult.error);
          } else {
            console.log(`Push notification sent successfully for appointment ${appointment_id}`);
          }
        }
      } catch (notificationError) {
        // Log notification error but don't fail the appointment status update
        console.error(`Failed to send push notification for appointment ${appointment_id}:`, notificationError);
      }
    }

    return res.status(200).json({ 
      success: true, 
      data: updated,
      message: `Appointment ${normalizedStatus.toLowerCase()} successfully${updated.cust_id ? ' and customer notified' : ''}`
    });
  } catch (error) {
    console.error("Error updating appointment status:", error);
    return res.status(500).json({ success: false, message: "Server error" });
  }
};

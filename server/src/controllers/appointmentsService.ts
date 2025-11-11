// src/services/appointmentsService.ts
import { Appointment, IAppointment } from "../models/Appointments";
import { IUnavailability } from "../models/Unavailability";
import { sendBulkNotifications } from "../utils/pushNotifications";

export const cancelAffectedAppointments = async (unavailability: IUnavailability) => {
  try {
    const dateStr = unavailability.date_unavailable;

    let filter: any = { 
      status: "Approved",
      date_for_inquiry: dateStr
    };

    if (unavailability.type === "Partial Day") {
      // Partial day: filter appointments that overlap with partial hours
      filter.time_start = { $lt: unavailability.time_end };
      filter.time_end = { $gt: unavailability.time_start };
    }

    const affectedAppointments: IAppointment[] = await Appointment.find(filter);

    if (affectedAppointments.length === 0) return; // nothing to cancel

    const affectedIds = affectedAppointments.map(a => a._id);

    // Update appointment statuses to cancelled
    // Normalize cancellation status to American spelling 'Canceled' in stored records
    await Appointment.updateMany(
      { _id: { $in: affectedIds } },
      { $set: { status: "Canceled", cancel_reason: `Canceled due to unavailability (${unavailability.type})` } }
    );

    console.log(`Canceled ${affectedAppointments.length} appointment(s) affected by unavailability on ${dateStr}`);

    // Send push notifications to affected customers
    if (affectedAppointments.length > 0) {
      try {
        const customerIds = affectedAppointments.map(appointment => appointment.cust_id);
        
        // Format the date for notification message
        const notificationDate = new Date(dateStr).toLocaleDateString('en-US', {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        });

  let notificationTitle = "Appointment Canceled";
        let notificationBody;

        if (unavailability.type === "Full Day") {
          notificationBody = `Your appointment on ${notificationDate} has been canceled due to unavailability for the full day.`;
        } else {
          // Partial Day
          const timeStart = unavailability.time_start || "N/A";
          const timeEnd = unavailability.time_end || "N/A";
          notificationBody = `Your appointment on ${notificationDate} has been canceled due to unavailability from ${timeStart} to ${timeEnd}.`;
        }

        // Add additional data for the notification
        const notificationData = {
          type: 'appointment_cancelled_unavailability',
          date: dateStr,
          unavailabilityType: unavailability.type,
          ...(unavailability.type === "Partial Day" && {
            timeStart: unavailability.time_start,
            timeEnd: unavailability.time_end
          }),
          reason: 'unavailability'
        };

        // Send bulk notifications to all affected customers (notification type remains unchanged)
        const notificationResult = await sendBulkNotifications(
          customerIds,
          notificationTitle,
          notificationBody,
          notificationData
        );

        console.log(`Push notifications sent for cancelled appointments:`, {
          totalSent: notificationResult.totalSent,
          successful: notificationResult.successful,
          failed: notificationResult.failed
        });

        if (notificationResult.failed > 0) {
          console.warn(`${notificationResult.failed} notifications failed to send for unavailability cancellations`);
        }

      } catch (notificationError) {
        // Log notification error but don't fail the cancellation process
        console.error("Failed to send push notifications for cancelled appointments:", notificationError);
      }
    }

  } catch (err) {
    console.error("Error cancelling affected appointments:", err);
  }
};

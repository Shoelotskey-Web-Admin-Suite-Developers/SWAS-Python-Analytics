/// src/models/Unavailability.ts
import mongoose, { Schema, Document } from "mongoose";

export interface IUnavailability extends Document {
  unavailability_id: string; // UNAV-001 style
  branch_id: string; // Reference to branch.branch_id
  date_unavailable: Date;
  type: "Full Day" | "Partial Day";
  time_start?: string; // e.g., "09:00" (only if Partial Day)
  time_end?: string;   // e.g., "12:00" (only if Partial Day)
  note?: string;       // e.g., "Meeting", "Holiday"
}

const UnavailabilitySchema: Schema = new Schema<IUnavailability>(
  {
    unavailability_id: { type: String, required: true, unique: true }, // e.g., UNAV-001
    branch_id: { type: String, required: true, ref: "Branch" },        // FK to Branch collection
    date_unavailable: { type: Date, required: true },
    type: { type: String, enum: ["Full Day", "Partial Day"], required: true },
    time_start: { type: String, default: null }, // optional, store as "HH:mm"
    time_end: { type: String, default: null },   // optional, store as "HH:mm"
    note: { type: String, maxlength: 255, default: null }, // optional
  }
);

export const Unavailability = mongoose.model<IUnavailability>(
  "Unavailability",
  UnavailabilitySchema,
  "unavailability"
);

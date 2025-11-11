import mongoose, { Schema, Document } from "mongoose";

export interface IAnnouncement extends Document {
  announcement_id: string;
  announcement_title: string;
  announcement_description?: string;
  announcement_date: Date;
  branch_id: string;
}

const AnnouncementSchema: Schema<IAnnouncement> = new Schema(
  {
    announcement_id: { type: String, required: true, unique: true },
    announcement_title: { type: String, required: true, maxlength: 100 },
    announcement_description: { type: String, default: null },
    announcement_date: { type: Date, default: Date.now, required: true },
    branch_id: { type: String, required: true },
  }
);

export const Announcement = mongoose.model<IAnnouncement>(
  "Announcements",
  AnnouncementSchema,
  "announcements"
);

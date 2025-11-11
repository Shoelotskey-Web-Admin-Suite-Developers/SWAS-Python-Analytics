/// src/models/Promo.ts
import mongoose, { Schema, Document } from "mongoose";

export interface IPromo extends Document {
  promo_id: string; // PROMO-001 style
  promo_title: string;
  promo_description?: string;
  promo_dates: Date[];      // ✅ new array of actual dates
  promo_duration: string;   // display string, e.g., "Sep 9–15, 2025"
  branch_id: string;
}

const PromoSchema: Schema = new Schema<IPromo>(
  {
    promo_id: { type: String, required: true, unique: true }, // e.g., PROMO-001
    promo_title: { type: String, required: true, maxlength: 100 },
    promo_description: { type: String, default: null },
    promo_dates: { type: [Date], required: true },           // store actual dates
    promo_duration: { type: String, required: true, maxlength: 255 }, // display string
    branch_id: { type: String, required: true },
  },
  { timestamps: true }
);

export const Promo = mongoose.model<IPromo>(
  "Promo",
  PromoSchema,
  "promos"
);

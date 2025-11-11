// src/models/DailyRevenue.ts
import mongoose, { Schema, Document } from "mongoose";

export interface IDailyRevenue extends Document {
  date: Date; // YYYY-MM-DD stored as Date
  total: number;
  branches: Map<string, number>; // dynamic branch revenues
}

const DailyRevenueSchema: Schema = new Schema<IDailyRevenue>(
  {
    date: { type: Date, required: true, unique: true },
    total: { type: Number, required: true },
    branches: {
      type: Map,
      of: Number,
      required: true,
    },
  },
  {
    strict: false, // keep raw flat structure like "SMGRA-B-NCR": 5225
    toJSON: { virtuals: true },
    toObject: { virtuals: true },
  }
);

export const DailyRevenue = mongoose.model<IDailyRevenue>(
  "DailyRevenue",
  DailyRevenueSchema,
  "sales_over_time" // collection name
);

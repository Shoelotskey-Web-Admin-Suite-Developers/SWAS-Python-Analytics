// src/models/Service.ts
import mongoose, { Schema, Document } from "mongoose";

export interface IService extends Document {
  service_id: string;
  service_base_price: number;
  service_type: "Service" | "Additional";
  service_duration: number;
  service_name: string;
  service_description?: string;
}

const ServiceSchema: Schema = new Schema<IService>(
  {
    service_id: { type: String, required: true, unique: true },
    service_base_price: { type: Number, required: true },
    service_type: { type: String, enum: ["Service", "Additional"], required: true },
    service_duration: { type: Number, required: true },
    service_name: { type: String, required: true },
    service_description: { type: String, default: null },
  }
);

// Explicit collection name
export const Service = mongoose.model<IService>("Service", ServiceSchema, "services");

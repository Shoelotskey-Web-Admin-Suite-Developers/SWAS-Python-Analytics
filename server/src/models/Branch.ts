/// src/models/Branch.ts
import mongoose, { Schema, Document } from "mongoose";

export interface IBranch extends Document {
  branch_id: string; // <CODE>-<TYPE>-LOC, e.g., VAL-BRANCH-LOC
  branch_number: number;
  branch_name: string; // Human-readable branch name
  location: string; // e.g., "Valenzuela, NCR"
  branch_code: string; // e.g., VAL, SMV
  type: "H" | "B" | "W"; // Hub or Branch
}

const BranchSchema: Schema = new Schema<IBranch>(
  {
    branch_id: { type: String, required: true, unique: true }, // <CODE>-<TYPE>-LOC
    branch_number: { type: Number, required: true, unique: true },
    branch_name: { type: String, required: true, maxlength: 100 }, // NEW
    location: { type: String, required: true, maxlength: 100 },
    branch_code: { type: String, required: true, unique: true, maxlength: 20 },
    type: { type: String, enum: ["H", "B", "W"], required: true },
  }
  // no timestamps
);

export const Branch = mongoose.model<IBranch>(
  "Branch",
  BranchSchema,
  "branches"
);

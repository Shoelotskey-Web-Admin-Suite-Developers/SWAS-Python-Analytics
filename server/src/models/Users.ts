/// src/models/Users.ts
import mongoose, { Schema, Document } from "mongoose";

export interface IUser extends Document {
  user_id: string; // NCR-VAL-B style (REG-<BRANCHCODE>-<TYPE>)
  branch_id: string; // FK -> Branch
  password: string; // hashed password
}

const UserSchema: Schema = new Schema<IUser>(
  {
    user_id: { type: String, required: true, unique: true }, // e.g., NCR-VAL-B
    branch_id: { type: String, required: true, ref: "Branch" },
    password: { type: String, required: true },
  }
  // no timestamps
);

export const User = mongoose.model<IUser>(
  "User",
  UserSchema,
  "users"
);

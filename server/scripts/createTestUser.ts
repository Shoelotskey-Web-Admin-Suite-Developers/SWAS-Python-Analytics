import mongoose from "mongoose";
import bcrypt from "bcryptjs";
import { User } from "../src/models/Users";
import dotenv from "dotenv";

dotenv.config();
const MONGO_URI = process.env.MONGO_URI || "";

async function createTestUser() {
  await mongoose.connect(MONGO_URI);
  console.log("Connected to MongoDB");

  const password = "123456"; // plain password
  const hashedPassword = await bcrypt.hash(password, 10);

  const user = new User({
    user_id: "NCR-VAL-B",
    user_number: 1,
    branch_id: "VALEN",
    position: "Admin",
    password: hashedPassword,
  });

  await user.save();
  console.log("✅ Test user created!");
  mongoose.disconnect();
}

createTestUser().catch(console.error);

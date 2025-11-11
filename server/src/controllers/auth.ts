// src/controllers/auth.ts
import { Request, Response } from "express";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { User } from "../models/Users";

const JWT_SECRET = process.env.JWT_SECRET || "supersecretkey"; // set in .env for production
const JWT_EXPIRES_IN = "1h"; // token validity

export const login = async (req: Request, res: Response) => {
  try {
    const { user_id, password } = req.body;
    console.log("Received user_id:", user_id);
    console.log("Received password:", password);

    if (!user_id || !password) {
      return res.status(400).json({ message: "user_id and password required" });
    }

    // Find user by user_id
    const user = await User.findOne({ user_id });
    if (!user) {
      return res.status(401).json({ message: "Invalid credentials" });
    }

    // Compare password
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(401).json({ message: "Invalid credentials" });
    }

    // Generate JWT
    const token = jwt.sign(
      { user_id: user.user_id, branch_id: user.branch_id },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    // Return token and basic user info
    return res.json({
      token,
      user: {
        user_id: user.user_id,
        branch_id: user.branch_id,
      },
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ message: "Server error" });
  }
};

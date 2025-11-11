import { Request, Response } from "express";
import bcrypt from "bcryptjs";
import { User } from "../models/Users";

export const addUser = async (req: Request, res: Response) => {
  try {
    const { user_id, branch_id, password } = req.body;

    if (!user_id || !branch_id || !password) {
      return res.status(400).json({ message: "All fields are required." });
    }

    // Check if user_id already exists
    const existingUser = await User.findOne({ user_id });
    if (existingUser) {
      return res.status(409).json({ message: "User ID already exists." });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);

    const newUser = new User({
      user_id,
      branch_id,
      password: hashedPassword,
    });

    await newUser.save();

    return res.status(201).json({
      message: "User created successfully",
      user: {
        user_id: newUser.user_id,
        branch_id: newUser.branch_id,
      },
    });
  } catch (error) {
    console.error("Error adding user:", error);
    return res.status(500).json({ message: "Server error" });
  }
};

// Get all users
export const getUsers = async (req: Request, res: Response) => {
  try {
    const users = await User.find({}, { password: 0 }); // exclude password
    return res.status(200).json(users);
  } catch (error) {
    console.error("Error fetching users:", error);
    return res.status(500).json({ message: "Server error" });
  }
};

// Delete a user by user_id
export const deleteUser = async (req: Request, res: Response) => {
  try {
    const { user_id } = req.params;

    if (!user_id) {
      return res.status(400).json({ message: "User ID is required." });
    }

    const deletedUser = await User.findOneAndDelete({ user_id });

    if (!deletedUser) {
      return res.status(404).json({ message: "User not found." });
    }

    return res.status(200).json({ message: "User deleted successfully." });
  } catch (error) {
    console.error("Error deleting user:", error);
    return res.status(500).json({ message: "Server error" });
  }
};

// Edit a user by user_id (user_id is read-only)
export const editUser = async (req: Request, res: Response) => {
  try {
    const { user_id } = req.params; // identify the user
    const { branch_id, password } = req.body;

    if (!user_id) {
      return res.status(400).json({ message: "User ID is required." });
    }

    const user = await User.findOne({ user_id });
    if (!user) {
      return res.status(404).json({ message: "User not found." });
    }

    if (branch_id) user.branch_id = branch_id;
    if (password) user.password = await bcrypt.hash(password, 10);

    await user.save();

    return res.status(200).json({
      message: "User updated successfully",
      user: {
        user_id: user.user_id,
        branch_id: user.branch_id,
      },
    });
  } catch (error) {
    console.error("Error updating user:", error);
    return res.status(500).json({ message: "Server error" });
  }
};

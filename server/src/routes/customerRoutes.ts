// src/routes/customerRoutes.ts
import { Router } from "express";
import { 
  getCustomers, 
  getCustomerSummaries,
  getCustomerById, 
  getCustomerByNameAndBdate, 
  deleteCustomer, 
  updateCustomer, 
  deleteAllCustomers 
} from "../controllers/customerController";

const router = Router();

router.get("/", getCustomers);
router.get("/summary", getCustomerSummaries);
router.get("/search/by-name-birthday", getCustomerByNameAndBdate);
router.get("/:cust_id", getCustomerById);
router.put("/:cust_id", updateCustomer);
router.delete("/:cust_id", deleteCustomer);

// Delete all customers
router.delete("/", deleteAllCustomers);

export default router;

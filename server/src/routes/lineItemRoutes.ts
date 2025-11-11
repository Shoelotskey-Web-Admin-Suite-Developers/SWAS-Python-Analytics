// src/routes/lineItemRoutes.ts
import { Router } from "express";
import { 
  getLineItemsByStatus, 
  updateLineItemStatus, 
  getAllLineItems, 
  updateLineItemImage, 
  updateLineItemStorageFee, 
  getLineItemsByBranchId, 
  getLineItemsByLocation, 
  updateLineItemLocation, 
  getLineItemsByTransactionId,
  updateLineItem, // Add this import
  deleteLineItemsByTransactionId // Add this import
} from "../controllers/lineItemController";

const router = Router();


router.get("/status/:status", getLineItemsByStatus);
router.get("/branch/:branch_id", getLineItemsByBranchId);
router.get("/location/:location", getLineItemsByLocation);
router.get("/transaction/:transaction_id", getLineItemsByTransactionId);
router.get("/", getAllLineItems);
router.put("/status", updateLineItemStatus); // new route for updating status
router.put("/:line_item_id/image", updateLineItemImage);
router.put("/:line_item_id/storage-fee", updateLineItemStorageFee);
router.put("/:line_item_id/location", updateLineItemLocation);
router.put("/:line_item_id", updateLineItem); // Add this new general update route
router.delete("/transaction/:transaction_id", deleteLineItemsByTransactionId); // Add this route

export default router;

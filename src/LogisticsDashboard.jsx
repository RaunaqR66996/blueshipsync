import React, { useState } from 'react';
import AuthSystem from './AuthSystem';
import ShippingDashboard from './ShippingDashboard';
import InventoryManagement from './InventoryManagement';
import ShipmentManagement from './ShipmentManagement';
import CarrierManagement from './CarrierManagement';
import ReportingAnalytics from './ReportingAnalytics';

export default function LogisticsDashboard() {
  const [activeTab, setActiveTab] = useState('auth');

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-7 gap-2">
          <TabsTrigger value="auth">Auth</TabsTrigger>
          <TabsTrigger value="shippingDashboard">Shipping Dashboard</TabsTrigger>
          <TabsTrigger value="inventoryManagement">Inventory Management</TabsTrigger>
          <TabsTrigger value="shipmentManagement">Shipment Management</TabsTrigger>
          <TabsTrigger value="carrierManagement">Carrier Management</TabsTrigger>
          <TabsTrigger value="reportingAnalytics">Reporting & Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="auth">
          <AuthSystem />
        </TabsContent>

        <TabsContent value="shippingDashboard">
          <ShippingDashboard />
        </TabsContent>

        <TabsContent value="inventoryManagement">
          <InventoryManagement />
        </TabsContent>

        <TabsContent value="shipmentManagement">
          <ShipmentManagement />
        </TabsContent>

        <TabsContent value="carrierManagement">
          <CarrierManagement />
        </TabsContent>

        <TabsContent value="reportingAnalytics">
          <ReportingAnalytics />
        </TabsContent>
      </Tabs>
    </div>
  );
}

import React, { useState } from 'react';
import './BlueShipSync.css';

// Mock Data
const mockOrders = [
  {
    id: 'ORD-1001',
    customerName: 'John Doe',
    email: 'john@example.com',
    status: 'processing',
    orderDate: '2023-05-14',
    totalAmount: 125.99,
  },
];

const statusOptions = [
  { value: 'all', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'shipped', label: 'Shipped' },
  { value: 'delivered', label: 'Delivered' },
];

const sortOptions = [
  { value: 'newest', label: 'Newest First' },
  { value: 'oldest', label: 'Oldest First' },
];

const warehouseOptions = [
  { value: 'east', label: 'East Coast Facility' },
];

const menuItems = [
  'Dashboard',
  'Inventory Receiving (NFC)',
  'Carrier Selection',
  'Order Processing',
  'Live Location',
  'Order History',
  'Settings',
];

function getStatusLabel(status) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function getStatusClass(status) {
  switch (status) {
    case 'pending':
      return 'status status-pending';
    case 'processing':
      return 'status status-processing';
    case 'shipped':
      return 'status status-shipped';
    case 'delivered':
      return 'status status-delivered';
    default:
      return 'status';
  }
}

export default function OrderManagement() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortOption, setSortOption] = useState('newest');
  const [selectedWarehouse, setSelectedWarehouse] = useState('east');
  const [showWarehouseDropdown, setShowWarehouseDropdown] = useState(false);

  const filteredOrders = mockOrders.filter(order => {
    const matchesSearch =
      order.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.customerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus =
      statusFilter === 'all' || order.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const sortedOrders = [...filteredOrders].sort((a, b) => {
    if (sortOption === 'newest') {
      return new Date(b.orderDate) - new Date(a.orderDate);
    } else {
      return new Date(a.orderDate) - new Date(b.orderDate);
    }
  });

  // Summary counts
  const summary = {
    total: mockOrders.length,
    pending: mockOrders.filter(o => o.status === 'pending').length,
    processing: mockOrders.filter(o => o.status === 'processing').length,
    shipped: mockOrders.filter(o => o.status === 'shipped').length,
    delivered: mockOrders.filter(o => o.status === 'delivered').length,
  };

  return (
    <div className="order-mgmt-root">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">BlueShipSync</div>
        <ul className="sidebar-menu">
          {menuItems.map(item => (
            <li
              key={item}
              className={`sidebar-menu-item${item === 'Settings' ? ' active' : ''}`}
            >
              {item}
            </li>
          ))}
        </ul>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <div className="main-header">
          <h1>Order Management</h1>
          <div className="warehouse-dropdown">
            <button
              className="warehouse-btn"
              onClick={() => setShowWarehouseDropdown(v => !v)}
            >
              {warehouseOptions.find(w => w.value === selectedWarehouse).label}
              <span className="dropdown-arrow">&#9660;</span>
            </button>
            {showWarehouseDropdown && (
              <div className="warehouse-list">
                {warehouseOptions.map(wh => (
                  <div
                    key={wh.value}
                    className={`warehouse-option${wh.value === selectedWarehouse ? ' selected' : ''}`}
                    onClick={() => {
                      setSelectedWarehouse(wh.value);
                      setShowWarehouseDropdown(false);
                    }}
                  >
                    {wh.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="filters-summary-row">
          {/* Filters */}
          <section className="filters-card">
            <h2>Filters</h2>
            <input
              type="text"
              className="search-input"
              placeholder="Search orders..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
            <div className="filters-row">
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
              >
                {statusOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <select
                value={sortOption}
                onChange={e => setSortOption(e.target.value)}
              >
                {sortOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </section>

          {/* Summary */}
          <section className="summary-card">
            <h2>Summary</h2>
            <div className="summary-grid">
              <div>
                <div className="summary-value">{summary.total}</div>
                <div className="summary-label">Total Orders</div>
              </div>
              <div>
                <div className="summary-value">{summary.pending}</div>
                <div className="summary-label">Pending</div>
              </div>
              <div>
                <div className="summary-value">{summary.processing}</div>
                <div className="summary-label">Processing</div>
              </div>
              <div>
                <div className="summary-value">{summary.shipped}</div>
                <div className="summary-label">Shipped</div>
              </div>
              <div>
                <div className="summary-value">{summary.delivered}</div>
                <div className="summary-label">Delivered</div>
              </div>
            </div>
          </section>
        </div>

        {/* Orders Table */}
        <section className="orders-table-card">
          <div className="orders-table-header">
            <div>
              <h2>Orders</h2>
              <span className="orders-found">{sortedOrders.length} orders found</span>
            </div>
            <button
              className="reset-btn"
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('all');
                setSortOption('newest');
              }}
            >
              Reset Filters
            </button>
          </div>
          <table className="orders-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Customer</th>
                <th>Date</th>
                <th>Status</th>
                <th className="right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {sortedOrders.map(order => (
                <tr key={order.id}>
                  <td className="order">{order.id}</td>
                  <td>
                    <div className="order">{order.customerName}</div>
                    <div className="order">{order.email}</div>
                  </td>
                  <td className="order">{order.orderDate.split('-').reverse().join('/')}</td>
                  <td className="order">
                    <span className={getStatusClass(order.status)}>
                      {getStatusLabel(order.status)}
                    </span>
                  </td>
                  <td className="right">${order.totalAmount.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}

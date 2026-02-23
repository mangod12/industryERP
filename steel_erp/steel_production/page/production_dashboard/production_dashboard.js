// Production Dashboard JavaScript
frappe.pages['production-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Production Dashboard',
		single_column: true
	});

	// Add refresh button
	page.set_primary_action('Refresh', function() {
		load_dashboard_data();
	}, 'fa fa-refresh');

	// Create dashboard layout
	page.dashboard = $('<div class="production-dashboard"></div>').appendTo(page.main);

	// Load dashboard data
	load_dashboard_data();

	// Auto-refresh every 10 seconds
	setInterval(load_dashboard_data, 10000);

	function load_dashboard_data() {
		frappe.call({
			method: 'steel_erp.steel_production.page.production_dashboard.production_dashboard.get_dashboard_data',
			callback: function(r) {
				if (r.message) {
					render_dashboard(r.message);
				}
			}
		});
	}

	function render_dashboard(data) {
		let html = `
			<div class="row">
				<div class="col-md-12">
					<h3>Steel Production Overview</h3>
				</div>
			</div>

			<!-- KPI Cards -->
			<div class="row" style="margin-top: 20px;">
				<div class="col-md-3">
					<div class="card">
						<div class="card-body text-center">
							<h4 style="color: #5e64ff;">${data.total_orders}</h4>
							<p>Total Orders</p>
						</div>
					</div>
				</div>
				<div class="col-md-3">
					<div class="card">
						<div class="card-body text-center">
							<h4 style="color: #ffa00a;">${data.in_progress}</h4>
							<p>In Progress</p>
						</div>
					</div>
				</div>
				<div class="col-md-3">
					<div class="card">
						<div class="card-body text-center">
							<h4 style="color: #98d85b;">${data.completed}</h4>
							<p>Completed</p>
						</div>
					</div>
				</div>
				<div class="col-md-3">
					<div class="card">
						<div class="card-body text-center">
							<h4 style="color: #ff5858;">${data.on_hold}</h4>
							<p>On Hold</p>
						</div>
					</div>
				</div>
			</div>

			<!-- Stage Summary -->
			<div class="row" style="margin-top: 30px;">
				<div class="col-md-12">
					<h4>Production Stages</h4>
					<table class="table table-bordered">
						<thead>
							<tr>
								<th>Stage</th>
								<th>Not Started</th>
								<th>In Progress</th>
								<th>Completed</th>
							</tr>
						</thead>
						<tbody>
							${render_stage_rows(data.stage_summary)}
						</tbody>
					</table>
				</div>
			</div>

			<!-- Inventory Summary -->
			<div class="row" style="margin-top: 30px;">
				<div class="col-md-12">
					<h4>Material Inventory</h4>
					<table class="table table-bordered">
						<thead>
							<tr>
								<th>Material</th>
								<th>Available (kg)</th>
								<th>Consumed (kg)</th>
								<th>Utilization %</th>
								<th>Status</th>
							</tr>
						</thead>
						<tbody>
							${render_inventory_rows(data.inventory_summary)}
						</tbody>
					</table>
				</div>
			</div>
		`;

		page.dashboard.html(html);
	}

	function render_stage_rows(stage_summary) {
		if (!stage_summary || stage_summary.length === 0) {
			return '<tr><td colspan="4" class="text-center">No data</td></tr>';
		}

		return stage_summary.map(stage => `
			<tr>
				<td><strong>${stage.stage_name}</strong></td>
				<td>${stage.not_started || 0}</td>
				<td><span class="indicator orange">${stage.in_progress || 0}</span></td>
				<td><span class="indicator green">${stage.completed || 0}</span></td>
			</tr>
		`).join('');
	}

	function render_inventory_rows(inventory) {
		if (!inventory || inventory.length === 0) {
			return '<tr><td colspan="5" class="text-center">No inventory data</td></tr>';
		}

		return inventory.map(item => {
			let status_color = item.utilization > 85 ? 'red' : item.utilization > 70 ? 'orange' : 'green';
			return `
				<tr>
					<td>${item.item_name}</td>
					<td>${item.available.toFixed(2)}</td>
					<td>${item.consumed.toFixed(2)}</td>
					<td><span class="indicator ${status_color}">${item.utilization.toFixed(1)}%</span></td>
					<td><span class="label label-${status_color}">${item.status}</span></td>
				</tr>
			`;
		}).join('');
	}
};

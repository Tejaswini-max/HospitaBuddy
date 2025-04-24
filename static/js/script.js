$(document).ready(function() {
    // Handle form submission
    $('#cssdForm').on('submit', function(e) {
        e.preventDefault();
        
        // Hide any previous results or errors
        $('#resultsCard').addClass('d-none');
        $('#errorAlert').addClass('d-none');
        
        // Get the bed count value
        const bedCount = $('#bed_count').val();
        
        // Validate input
        if (!bedCount || bedCount <= 0) {
            showError('Please enter a valid number of beds');
            return;
        }
        
        // Show loading indicator
        const submitBtn = $(this).find('button[type="submit"]');
        const originalBtnText = submitBtn.html();
        submitBtn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Calculating...');
        submitBtn.prop('disabled', true);
        
        // Send the form data to the server
        $.ajax({
            url: '/calculate',
            type: 'POST',
            data: $(this).serialize(),
            success: function(response) {
                // Reset button
                submitBtn.html(originalBtnText);
                submitBtn.prop('disabled', false);
                
                // Check if there's an error in the response
                if (response.error) {
                    showError(response.error);
                    return;
                }
                
                // Display the results
                displayResults(response);
            },
            error: function() {
                // Reset button
                submitBtn.html(originalBtnText);
                submitBtn.prop('disabled', false);
                
                // Show error message
                showError('An error occurred while communicating with the server. Please try again.');
            }
        });
    });
    
    // Function to display results
    function displayResults(data) {
        // Update the results card with the data
        $('#cssdArea').text(data.cssd_area);
        $('#bedRange').text(data.bed_range);
        $('#autoclaveModel').text(data.autoclave_model);
        $('#autoclaveQuantity').text(data.autoclave_quantity);
        
        // Populate equipment table
        populateEquipmentTable(data.equipment);
        
        // Display official budget range if available
        if (data.official_budget && 
            (data.official_budget.min !== 'Not specified' || data.official_budget.max !== 'Not specified')) {
            
            let budgetText = '';
            if (data.official_budget.min !== 'Not specified') {
                budgetText += "₹" + Number(data.official_budget.min).toLocaleString();
            }
            
            if (data.official_budget.max !== 'Not specified') {
                if (budgetText) {
                    budgetText += " to ₹" + Number(data.official_budget.max).toLocaleString();
                } else {
                    budgetText += "₹" + Number(data.official_budget.max).toLocaleString();
                }
            }
            
            if (budgetText) {
                $('#officialBudget').text(budgetText);
            } else {
                $('#officialBudget').text('Not available');
            }
        } else {
            $('#officialBudget').text('Not available');
        }
        
        // Show the results card
        $('#resultsCard').removeClass('d-none');
        
        // Scroll to results
        $('html, body').animate({
            scrollTop: $('#resultsCard').offset().top - 20
        }, 300);
    }
    
    // Function to populate the equipment table
    function populateEquipmentTable(equipment) {
        const tableBody = $('#equipmentTableBody');
        
        // Clear existing rows
        tableBody.empty();
        
        // Variable to track total budget
        let totalBudget = 0;
        
        // Check if equipment data exists and is not empty
        if (equipment && equipment.length > 0) {
            // Update item count badge
            $('#itemCount').text(`${equipment.length} item${equipment.length !== 1 ? 's' : ''}`);
            
            // Add each equipment as a row
            equipment.forEach((item, index) => {
                const row = $('<tr>');
                
                // Data attribute for mobile details view
                row.attr('data-equipment-index', index);
                row.attr('data-name', item.name);
                row.attr('data-spec', item.specification);
                
                // Add row cells with mobile-optimized display
                row.append(`<td>${index + 1}</td>`);
                row.append(`<td>${item.name}</td>`);
                row.append(`<td class="d-none d-md-table-cell">${item.specification}</td>`);
                row.append(`<td class="text-center">${item.quantity}</td>`);
                
                // Format unit price with commas for thousands
                const unitPrice = item.unit_price === "Not specified" ? 
                    "Not specified" : 
                    "₹" + item.unit_price.toLocaleString();
                row.append(`<td class="d-none d-sm-table-cell">${unitPrice}</td>`);
                
                // Format total price with commas for thousands
                const totalPrice = item.total_price === "Not specified" ? 
                    "Not specified" : 
                    "₹" + item.total_price.toLocaleString();
                row.append(`<td>${totalPrice}</td>`);
                
                // Calculate total price for this item based on unit price and quantity
                let itemTotalPrice;
                
                // First check if total_price is already available as a number
                if (typeof item.total_price === 'number') {
                    itemTotalPrice = item.total_price;
                } else if (item.total_price !== 'Not specified' && !isNaN(Number(item.total_price))) {
                    // Try converting string total_price to number if possible
                    itemTotalPrice = Number(item.total_price);
                } else {
                    // If total_price isn't available, calculate from unit_price and quantity
                    const unitPrice = (typeof item.unit_price === 'number') ? 
                        item.unit_price : 
                        (item.unit_price !== 'Not specified' && !isNaN(Number(item.unit_price))) ? 
                            Number(item.unit_price) : 0;
                            
                    const quantity = (typeof item.quantity === 'number') ? 
                        item.quantity : 
                        (item.quantity !== 'Not specified' && !isNaN(Number(item.quantity))) ? 
                            Number(item.quantity) : 0;
                            
                    itemTotalPrice = unitPrice * quantity;
                }
                
                // Add to total budget if we calculated a valid price
                if (itemTotalPrice && !isNaN(itemTotalPrice)) {
                    totalBudget += itemTotalPrice;
                    
                    // Update the displayed total price if it was calculated differently
                    if (item.total_price === 'Not specified' && itemTotalPrice > 0) {
                        const calculatedPrice = "₹" + itemTotalPrice.toLocaleString();
                        row.find('td:last').text(calculatedPrice + " (calculated)");
                    }
                }
                
                tableBody.append(row);
            });
            
            // Update the total budget display
            $('#totalBudget').text("₹" + totalBudget.toLocaleString());
            
            // Add tap/click handler for equipment rows (for mobile detail view)
            $('#equipmentTableBody tr').not('.no-equipment-row').on('click', function() {
                const isMobile = window.innerWidth < 768;
                if (isMobile) {
                    const name = $(this).data('name');
                    const spec = $(this).data('spec');
                    
                    // Show details in a modal or tooltip
                    showMobileEquipmentDetails(name, spec);
                }
            });
            
        } else {
            // If no equipment data, show message
            tableBody.append(`
                <tr class="no-equipment-row">
                    <td colspan="6" class="text-center py-3">No equipment data available</td>
                </tr>
            `);
            
            // Reset total budget and item count
            $('#totalBudget').text("₹0");
            $('#itemCount').text("0 items");
        }
    }
    
    // Function to show equipment details on mobile
    function showMobileEquipmentDetails(name, specification) {
        // Check if modal exists, if not create it
        if ($('#equipmentDetailModal').length === 0) {
            const modalHTML = `
                <div class="modal fade equipment-detail-modal" id="equipmentDetailModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title">Equipment Details</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <h6 class="equipment-name fw-bold"></h6>
                                <p class="equipment-spec"></p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            $('body').append(modalHTML);
        }
        
        // Update modal content and show
        $('#equipmentDetailModal .equipment-name').text(name);
        $('#equipmentDetailModal .equipment-spec').text(specification);
        
        // Initialize and show the modal
        const detailModal = new bootstrap.Modal(document.getElementById('equipmentDetailModal'));
        detailModal.show();
    }
    
    // Function to show error message
    function showError(message) {
        $('#errorMessage').text(message);
        $('#errorAlert').removeClass('d-none');
        
        // Scroll to error
        $('html, body').animate({
            scrollTop: $('#errorAlert').offset().top - 20
        }, 300);
    }
});

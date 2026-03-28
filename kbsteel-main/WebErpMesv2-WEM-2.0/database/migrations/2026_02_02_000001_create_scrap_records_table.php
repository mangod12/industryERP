<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     * Scrap records for tracking waste materials after dispatch
     */
    public function up(): void
    {
        Schema::create('scrap_records', function (Blueprint $table) {
            $table->id();
            $table->string('material_name');
            $table->decimal('weight_kg', 10, 2);
            $table->decimal('length_mm', 10, 2)->nullable();
            $table->decimal('width_mm', 10, 2)->nullable();
            $table->decimal('thickness_mm', 10, 2)->nullable();
            $table->integer('quantity')->default(1);
            $table->string('reason_code'); // cutting_waste, defect, damage, overrun, leftover
            $table->string('stage')->nullable(); // fabrication, painting, dispatch
            $table->string('dimensions')->nullable(); // Text description
            $table->string('location')->nullable(); // Physical location
            $table->text('notes')->nullable();
            $table->string('status')->default('pending'); // pending, returned_to_inventory, moved_to_reusable, disposed, recycled, sold
            $table->decimal('scrap_value', 10, 2)->nullable(); // Sale value if sold
            
            // Traceability - using simple strings/integers to avoid complex FK dependencies
            $table->string('work_order_id')->nullable(); // Reference to work order
            $table->unsignedBigInteger('customer_id')->nullable(); // Optional customer reference
            
            // Audit
            $table->foreignId('created_by')->nullable()->constrained('users')->nullOnDelete();
            $table->foreignId('processed_by')->nullable()->constrained('users')->nullOnDelete();
            $table->timestamp('processed_at')->nullable();
            
            $table->timestamps();
            $table->softDeletes();
            
            // Indexes for performance
            $table->index('material_name');
            $table->index('status');
            $table->index('reason_code');
            $table->index('stage');
            $table->index('created_at');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('scrap_records');
    }
};

<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     * Reusable stock for tracking offcuts that can be used again
     */
    public function up(): void
    {
        Schema::create('reusable_stock', function (Blueprint $table) {
            $table->id();
            $table->string('material_name');
            $table->decimal('weight_kg', 10, 2);
            $table->decimal('length_mm', 10, 2)->nullable();
            $table->decimal('width_mm', 10, 2)->nullable();
            $table->decimal('thickness_mm', 10, 2)->nullable();
            $table->integer('quantity')->default(1);
            $table->string('dimensions')->nullable(); // Text description e.g., "1200mm x 150mm beam"
            $table->string('quality_grade')->default('B'); // A=good, B=minor defects, C=usable with caution
            $table->string('location')->nullable(); // Physical location in warehouse
            $table->text('notes')->nullable();
            
            // Status tracking
            $table->string('status')->default('available'); // available, reserved, used, returned, scrapped
            
            // Source traceability
            $table->foreignId('scrap_record_id')->nullable()->constrained('scrap_records')->nullOnDelete();
            
            // Usage tracking
            $table->string('used_for_work_order')->nullable();
            $table->timestamp('used_at')->nullable();
            $table->foreignId('used_by')->nullable()->constrained('users')->nullOnDelete();
            
            // Return tracking
            $table->timestamp('returned_at')->nullable();
            $table->foreignId('returned_by')->nullable()->constrained('users')->nullOnDelete();
            
            // Audit
            $table->foreignId('created_by')->nullable()->constrained('users')->nullOnDelete();
            
            $table->timestamps();
            $table->softDeletes();
            
            // Indexes for finding matching pieces
            $table->index('material_name');
            $table->index('status');
            $table->index('quality_grade');
            $table->index(['length_mm', 'width_mm', 'thickness_mm']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('reusable_stock');
    }
};

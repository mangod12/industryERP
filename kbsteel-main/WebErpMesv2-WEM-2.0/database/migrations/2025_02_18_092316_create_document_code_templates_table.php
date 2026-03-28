<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('document_code_templates', function (Blueprint $table) {
            $table->id();
            $table->string('document_type')->unique(); // The type of document (eg: quote, order, invoice)
            $table->string('template');               // The code generation template (ex: {year}-{id})
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('document_code_templates');
    }
};

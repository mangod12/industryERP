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
        Schema::table('tasks', function (Blueprint $table) {
            // add origine column
            //0 : WEM Enterprise task screen
            //1 : Import of standard task (task or BOM)
            //2 : Import of standard breakdown
            //3 : breakdown of composed component
            //4 : Created from a PO
            //5 : Duplication
            //6 : Wizard to convert a quotation into a sales order
            //7 : Interface RadQuote
            $table->string('origin')->nullable()->after('methods_tools_id');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('tasks', function (Blueprint $table) {
            // drop origine column
            $table->dropColumn('origin');
        });
    }
};

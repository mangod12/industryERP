<?php

namespace App\Http\Middleware;

use Closure;
use App\Models\Planning\Status;

class CheckTaskStatus
{
    public function handle($request, Closure $next)
    {
        $status = Status::select('id')->orderBy('order')->first();

        if (!$status) {
            return redirect()->route('admin.kanban.settings')->withErrors('Please add Kanban information before');
        }

        return $next($request);
    }
}

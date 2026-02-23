<?php

namespace App\Http\Controllers\Workshop;

use Illuminate\Http\Request;
use App\Models\Planning\Task;
use Illuminate\Support\Facades\DB;
use App\Http\Controllers\Controller;
use App\Models\Planning\TaskResources;

class WorkshopController extends Controller
{
    /**
     * @return \Illuminate\Contracts\View\View
     */
    public function index()
    {
        return view('workshop/workshop');
    }

    /**
     * @return \Illuminate\Contracts\View\View
     */
    public function taskLines()
    {
        return view('workshop/workshop-task-lines');
    }

    /**
     * Display the status of tasks in the workshop.
     *
     * This method calculates and returns various statistics related to tasks in the workshop, 
     * including the number of tasks in different statuses, the average processing time of tasks, 
     * user productivity, and resource allocation.
     *
     * @param \Illuminate\Http\Request $request The incoming request instance.
     * 
     * @return \Illuminate\View\View The view displaying the task status.
     *
     * Statistics returned:
     * - Number of tasks with status 'Open'
     * - Number of tasks with status 'In Progress'
     * - Number of tasks with status 'Pending'
     * - Number of tasks with status 'Supplied'
     * - Number of tasks with status 'Finished'
     * - Average processing time of tasks (in seconds)
     * - User productivity (number of tasks each user has worked on)
     * - Total number of resources allocated to tasks
     * - Total hours allocated to each resource
     */
    public function statu(Request $request)
    {
        // Number of current OFs
        $tasksOpen = Task::whereHas('status', function($query) {
            $query->where('title', 'Open');
        })->count();

        $tasksInProgress = Task::whereHas('status', function($query) {
            $query->where('title', 'In Progress');
        })->count();

        // État des OF
        $tasksPending = Task::whereHas('status', function($query) {
            $query->where('title', 'Pending');
        })->count();

        $tasksOngoing = Task::whereHas('status', function($query) {
            $query->where('title', 'Supplied');
        })->count();

        $tasksCompleted = Task::whereHas('status', function($query) {
            $query->where('title', 'Finished');
        })->count();

        // Calculation of the average OF processing time
        $averageProcessingTime = 0;
        $tasksWithEndDate = Task::whereNotNull('end_date')->get();
        if($tasksWithEndDate->count() > 0){
            $totalTime = $tasksWithEndDate->sum(function ($task) {
                return $task->getTotalLogTime() * 3600; //in second time
            });
            $averageProcessingTime = $totalTime / $tasksWithEndDate->count();
        }

        // User productivity
        $userProductivity = DB::table('task_activities')
            ->join('users', 'task_activities.user_id', '=', 'users.id')
            ->select('users.name', DB::raw('count(task_activities.id) as tasks_count'))
            ->groupBy('users.name')
            ->get();

        //Ressources Time
        $totalResourcesAllocated = TaskResources::count();
        $tasks = Task::with('resources')->get();

        $resourceHours = [];
        
        foreach ($tasks as $task) {
            foreach ($task->resources as $resource) {
                $resourceName = $resource->label;
                $totalTime = $task->TotalTime();
        
                if (array_key_exists($resourceName, $resourceHours)) {
                    $resourceHours[$resourceName] += $totalTime;
                } else {
                    $resourceHours[$resourceName] = $totalTime;
                }
            }
        }

        return view('workshop/workshop-task-statu', compact(
                                                    'tasksOpen',
                                                    'tasksInProgress',
                                                    'tasksPending',
                                                    'tasksOngoing',
                                                    'tasksCompleted',
                                                    'averageProcessingTime',
                                                    'userProductivity',
                                                    'totalResourcesAllocated',
                                                    'resourceHours'
                                                    ), ['TaskId' => $request->id]);
    }

    /**
     * Display the stock detail view.
     *
     * This method handles the request to display the stock detail view for a specific stock item.
     * It retrieves the stock item ID from the request and passes it to the view.
     *
     * @param \Illuminate\Http\Request $request The HTTP request instance.
     * @return \Illuminate\View\View The view for the stock detail page.
     */
    public function stockDetail(Request $request)
    {
        return view('workshop/workshop-stock-detail', ['StockDetailId' => $request->id]);
    }
    
}

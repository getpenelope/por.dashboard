angular.module('kanban', ['ngDragDrop'])
  .controller("KanbanCtrl", function($scope, $socketio) {

    $scope.columns = [];

    $scope.init = function(board_id){
        $scope.board_id = board_id;
        $socketio.emit("board_id", board_id);
    }

    $scope.addColumn = function() {
        $scope.columns.push({'title': 'New column ' + $scope.columns.length,
                             'wip': 0,
                             'tasks': []});
        $scope.boardChanged();
    };

    $scope.removeColumn = function(item) {
        if (item != 0){
          $scope.columns.splice(item, 1);
          $scope.boardChanged();
       };
    };

    $scope.boardChanged = function() {
        $socketio.emit("board_changed",
            $scope.columns.slice(1, $scope.columns.length));
    };

    $scope.handleDrop = function(event, ui) {
        $scope.boardChanged();
    }

    $socketio.on('columns', function(data) {
      $scope.columns = data.value;
    });


  })

.directive('inlineEdit', function() {
    return function(scope, element, attrs) {
       element.bind('click', function(){
          element.toggleClass('inactive');
          if(element.hasClass('inactive')){
              $(element).blur();
              scope.boardChanged();
          }
       });
    };
})

.factory("$socketio", function($rootScope) {
  var socket = io.connect('/kanban');
  return {
    on: function (eventName, callback) {
      socket.on(eventName, function () {
        var args = arguments;
        $rootScope.$apply(function () {
          callback.apply(socket, args);
        });
      });
    },
    emit: function (eventName, data, callback) {
      socket.emit(eventName, data, function () {
        var args = arguments;
        $rootScope.$apply(function () {
          if (callback) {
            callback.apply(socket, args);
          }
        });
      })
    }
  };
})

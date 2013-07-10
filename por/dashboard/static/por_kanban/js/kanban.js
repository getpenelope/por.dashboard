angular.module('kanban', ['ngDragDrop'])
  .controller("KanbanCtrl", function($scope, $socketio) {

    $scope.init = function(board_id){
        $scope.board_id = board_id;
        $socketio.emit("board_id", board_id);
    }

    $scope.columns = [];
    $socketio.on('columns', function(data) {
      $scope.columns = data.value;
    });

    $scope.dropCallback = function(event, ui){
        $socketio.emit("board_changed", $scope.columns);
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


function check_number(number){
    if(isNaN(number)||(number<0))
    {
        number=0;
    }
    else if (number>100)
    {
        number=100;
    }
    return number;
}





















$(document).ready(function() {

    (function($) {
        $.fn.kanban = function() {
            var board = this;
            var board_id = $(this).data('board_id');
            this.add_col = function(col) {
                $(".task_pool_header:last").addClass("dotted_separator");
                $(".task_pool:last").addClass("dotted_separator");
                $("#task_pool_header_container").append('<th class="task_pool_header"><div class="header_name click"><img class="title_bullet" src="/fanstatic/por/por_kanban/img/mookup/bullet.png" /><span>'+col.title+'</span></div><div wip="'+col.wip+'" class="WIP">WIP: '+col.wip+'</div></th>');
                var task_pool = $('<td class="task_pool"><div /></td>');
                $("#task_pool_container").append(task_pool);
                $(col.tasks).each(function(){
                        task_pool.append(' \
                        <div class="big_container" id="'+this.id+'"> \
                            <div class="box_itm rounded">' + this.text + '</div> \
                            <div class="shadow" /> \
                            <div>');
                });
                board.intialize_sortables();
            };

            this.get_data = function() {
                $.getJSON(board_id + '/get_board_data.json', function(data) {
                    $(board).data('board', data);
                    board.render();
                });
            };

            this.set_data = function() {
                $.post(board_id + '/set_board_data.json', {board: JSON.stringify($(board).data('board'))})
            };

            this.serialize = function(){
                data = [];
                $(this).find('.header_name').each(function(col_index){
                    var title = $(this).children("span").html();
                    var wip = $(this).parent().children("div:eq(1)").attr("wip");
                    column = {'wip': wip,
                              'tasks': [],
                              'title': title}
                    $($(board).find('.task_pool:eq('+col_index+') .big_container')).each(function(){
                        column.tasks.push({'id':$(this).attr('id'),
                                           'text': $(this).find('.box_itm').html()})
                    });
                    if (title != 'Backlog') {
                        data.push(column);
                    };
                });
                $(this).data('board', data);
                board.set_data();
                return this;
            };

            this.intialize_sortables = function(){
                $(board).find(".task_pool" ).sortable({
                        connectWith: ".task_pool",
                        delay:25,
                        revert:true,
                        dropOnEmpty: true,
                        forcePlaceHolderSize: true,
                        helper: 'clone',
                        forceHelperSize: true,
                        receive: function(event, ui) {
                                var itms= $(this).children(".big_container").length;
                                var index=$(this).index();
                                var wip=  $(this).parent().parent().children("tr th:eq("+index+")").children("div:eq(1)").first().attr("wip");
                                wip = check_number(wip);
                                if((wip!=0)&&(itms>wip))
                                {
                                    $(ui.sender).sortable('cancel');
                                } else {
                                    board.serialize();
                                };
                            }
                });
            };

            this.render = function(){
                // first cleanup
                $('#add_col').click(function(){
                    var col= {'tasks': [],
                              'title': $(board).find(".task_pool").size(),
                              'wip': 0}
                    board.add_col(col);
                    board.serialize();
                });

                $('#remove_col').click(function(){
                    if($(board).find(".task_pool_header").size()>1){
                            $(board).find(".task_pool_header").last().remove();
                            $(board).find(".task_pool").last().remove();
                            $(board).find(".task_pool_header:last").removeClass("dotted_separator");
                            $(board).find(".task_pool:last").removeClass("dotted_separator");
                            board.intialize_sortables();
                            board.serialize();
                        }
                });

                $(board).find('.header_name').live('click',function(){
                    var cur_name=$(this).children("span").html();
                    var wip = $(this).parent().children("div:eq(1)").attr("wip");
                    wip = check_number(wip);
                    var header_new_html=' \
                    <div class="header_input"> \
                        Title<br/><input class="input header_input_name" value="'+cur_name+'" /> \
                    </div>  \
                    <div class="header_input"> \
                        WIP<br/><input class="input header_input_name" value="'+wip+'" /> \
                    </div>  \
                    <div class="small"> \
                        <div class="option save_header"><button class="btn btn-success btn-mini"><i class="icon-white icon-ok">&nbsp;</i></button></div> \
                    </div> \
                    <div class="clear"></div> \
                    ';
                    $(this).parent().html(header_new_html);
                });

                $(board).find('.save_header').live('click',function(){
                    var index=$(this).parent().parent().index();
                    var new_name=$(this).parent().parent().children("div:eq(0)").first().children(".input").first().val();
                    var wip=$(this).parent().parent().children("div:eq(1)").first().children(".input").first().val();
                    wip = check_number(wip);
                    if(index==0){
                        wip=0; // Primera columna debe tener el wip ilimitado
                    }
                    if(wip>0){
                        $(this).parent().parent().html('<div class="header_name click"><img class="title_bullet" src="/fanstatic/por/por_kanban/img/mookup/bullet.png" /><span class="title_text">'+new_name+'</span></div><div wip="'+wip+'" class="WIP">WIP: '+wip+'</div>');
                    } else{
                        $(this).parent().parent().html('<div class="header_name click"><img class="title_bullet" src="/fanstatic/por/por_kanban/img/mookup/bullet.png" /><span class="title_text">'+new_name+'</span></div><div wip="'+wip+'" class="WIP">WIP: Unlimited</div>');
                    };
                    board.serialize();
                });

                $($(this).data('board')).each(function() {
                    board.add_col(this);
                });
            }

        return this;
        }
    }(jQuery));

    //$('.kanban').kanban().get_data();

});

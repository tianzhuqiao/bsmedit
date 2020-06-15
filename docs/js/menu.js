$(window).on("load", function() {
// Cache selectors
var lastId,
    topMenu = $(".menu"),
    topTitleHeight = $(".toptitle").outerHeight()+15,
    topUL = topMenu.find('ul'),
    // All list items
    menuItems = topMenu.find("a"),
    // Anchors corresponding to menu items
    scrollItems = menuItems.map(function(){
        var item = $($(this).attr("href"));
        if (item.length) { return item; }
    });

var auto_hide_child_menu = menuItems.length > 15;
// Bind click handler to menu items so we can get a fancy scroll animation
if (!auto_hide_child_menu) {
    menuItems.click(function(e){
        var href = $(this).attr("href"),
            offsetTop = href === "#" ? 0 : $(href).offset().top-15+1;
        $('html, body').stop().animate({
            scrollTop: offsetTop
        }, 300);
        e.preventDefault();
    });
}

function update_menu() {
    // Get container scroll position
    var fromTop = $(this).scrollTop() + 15;

    // Get id of current scroll item
    var cur = scrollItems.map(function(){
        if ($(this).offset().top < fromTop)
            return this;
    });
    // Get the id of the current element
    cur = cur[cur.length-1];
    var id = cur && cur.length ? cur[0].id : "";

    if (lastId !== id) {
        lastId = id;
        // Set/remove active class
        menuItems.removeClass("active");
        menuItems.filter("[href='#"+id+"']").addClass("active");
        if (auto_hide_child_menu) {
            topUL.find('ul').each(function(index){
                $(this).css('display', 'none');
            });
        }
        menu = menuItems.filter("[href='#"+id+"']");
        menuul = menu.closest('ul').css('display', 'inline-block');
        menu.closest('li').children('ul').css('display', 'inline-block');
    }
}

// Bind to scroll
$(window).scroll(function(){
    update_menu();
});

update_menu();
});

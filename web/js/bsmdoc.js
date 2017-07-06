function isScrolledIntoView(elem) {
    var docViewTop = $(window).scrollTop();
    var docViewBottom = docViewTop + $(window).height();

    var elemTop = $(elem).offset().top;
    var elemBottom = elemTop + $(elem).height();

    return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
}
var simplePopup = (function() {
    var simplePopup = function(pattern) {
        this.pattern = pattern;
        this.target = false;
        var $container = $(document.body);
        this.tooltip = $('<div />').addClass('popup');
        $container.append(this.tooltip);
        this.tooltip.css({
            'background': '#ffa',
            'border' : '2px solid #A0A090',
            'padding': '3px 8px 3px 8px',
            'display': 'none',
            'width': '100%',
            'position': 'fixed',
            'z-index': '100',
            '-webkit-box-sizing': 'border-box',
            '-moz-box-sizing': 'border-box',
            'box-sizing': 'border-box',
        });
        var thispopup = this
        $container.on('mouseover', thispopup.pattern, {thispopup:thispopup}, thispopup.mouseOver);
        $container.on('mouseout', thispopup.pattern,  {thispopup:thispopup}, thispopup.mouseOut);
        this.showTooltip = false;
    };

    simplePopup.showTooltipNow = function(thispopup) {
        thispopup.showTooltip = true;
        thispopup.tooltip.stop(true, true);
        thispopup.tooltip.css({
            top: 0,
        });
        thispopup.tooltip.fadeIn();
    };

    simplePopup.prototype.keepVisible = function(e) {
        var thispopup = e.data.thispopup;
        thispopup.tooltip.stop();
        thispopup.tooltip.css({
            'opacity':'initial'
        });
    };
    simplePopup.prototype.mouseOver = function(e) {
        var thispopup = e.data.thispopup;
        var a = e.currentTarget;
        var $number = $(a.hash);
        var $root = $number.closest('div');
        if(thispopup.target) {
            thispopup.target.css({
                'background':'#fff',
            })
            thispopup.target = false;
        }
        if(isScrolledIntoView($root)) {
            // if the element is visible, highlight it by changing its background
            thispopup.target = $root;
            $root.css({
                'background':'#ffa',
            })
        } else {
            thispopup.showTooltip = true;
            var $container = $(document.body);
            thispopup.tooltip.bind('mouseover', {thispopup:thispopup}, thispopup.keepVisible);
            thispopup.tooltip.bind('mouseout',  {thispopup:thispopup}, thispopup.mouseOut);
            thispopup.tooltip.stop(true, true);
            thispopup.tooltip.html($root.html());
            thispopup.tooltip.css({
                top: 0,
            });
            thispopup.tooltip.fadeIn();
        }
    }

    simplePopup.prototype.mouseOut = function(e) {
        var thispopup = e.data.thispopup;
        thispopup.tooltip.stop(true, true);
        thispopup.tooltip.fadeOut(function () {
            thispopup.tooltip.empty();
        });
        if(thispopup.target) {
            thispopup.target.css({
                'background':'#fff',
            })
            thispopup.target = false;
        }
    }
    return simplePopup;
})();

$( window ).load(function() {
    new simplePopup('a[href*="mjx-eqn-"]');
    new simplePopup('a[href*="img-"]');
    new simplePopup('a[href*="tbl-"]');
    new simplePopup('a[href*="footnote-"]');
});

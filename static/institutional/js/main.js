(function ($) {
  "use strict";
  var windowOn = $(window);


    /*-----------------------------------------------------------------------------------

        Template Name: Artificial Intelligence Startup HTML5 Template
        Author: RRDevs
        Support: https://support.rrdevs.net
        Description: Artificial Intelligence Startup HTML5 Template
        Version: 1.0
        Developer: Soukhin khan (https://github.com/Soukhinkhan)

    -----------------------------------------------------------------------------------

      /*======================================
        Preloader activation
        ========================================*/
    
        handleQuantityButtons();
    
        $(document.body).on('updated_cart_totals', function() {
            handleQuantityButtons();
        });


        function resourcesHubMasonry() {
            var $grid = $('.resources-hub__masonry');
            $grid.masonry({
              itemSelector: '.col-item',
              columnWidth: '.col-lg-4',
              horizontalOrder: false,
              isAnimated: true,
              // percentPosition: true,
            });
        
            $grid.masonry('reloadItems');
            $grid.masonry('layout');
        
            // layout Masonry after each image loads
            $grid.imagesLoaded().progress(function () {
              $grid.masonry('layout');
            });
          }
        
          resourcesHubMasonry();


	$(window).on('load', function (event) {
		$('#preloader').delay(1000).fadeOut(500);

        $('.odometer').waypoint(function(direction) {
            if (direction === 'down') {
                let countNumber = $(this.element).attr("data-count");
                $(this.element).html(countNumber);
            }
        }, {
            offset: '80%'
        });
	});


    $(".preloader-close").on("click", function () {
        $('#preloader').delay(0).fadeOut(500);

        $('.odometer').waypoint(function(direction) {
            if (direction === 'down') {
                let countNumber = $(this.element).attr("data-count");
                $(this.element).html(countNumber);
            }
        }, {
            offset: '80%'
        });
    })

    //GSAP START

    // Check if any elements with the class ".end" exist
        if (document.querySelector('.end')) {
            // 31. Folks animation
            let endTl = gsap.timeline({
                repeat: -1,
                delay: 0.5,
                scrollTrigger: {
                    trigger: '.end',
                    start: 'bottom 100%-=50px'
                }
            });

            gsap.set('.end', {
                opacity: 0
            });

            gsap.to('.end', {
                opacity: 1,
                duration: 1,
                ease: 'power2.out',
                scrollTrigger: {
                    trigger: '.end',
                    start: 'bottom 100%-=50px',
                    once: true
                }
            });

            let mySplitText = new SplitText(".end", {
                type: "words,chars"
            });
            let chars = mySplitText.chars;
            let endGradient = chroma.scale(['#F9D371', '#F47340', '#EF2F88', '#8843F2']);
            
            endTl.to(chars, {
                duration: 0.5,
                scaleY: 0.6,
                ease: "power3.out",
                stagger: 0.04,
                transformOrigin: 'center bottom'
            });
            endTl.to(chars, {
                yPercent: -20,
                ease: "elastic",
                stagger: 0.03,
                duration: 0.8
            }, 0.5);
            endTl.to(chars, {
                scaleY: 1,
                ease: "elastic.out(2.5, 0.2)",
                stagger: 0.03,
                duration: 1.5
            }, 0.5);
            endTl.to(chars, {
                color: (i, el, arr) => {
                    return endGradient(i / arr.length).hex();
                },
                ease: "power2.out",
                stagger: 0.03,
                duration: 0.3
            }, 0.5);
            endTl.to(chars, {
                yPercent: 0,
                ease: "back",
                stagger: 0.03,
                duration: 0.8
            }, 0.7);
            endTl.to(chars, {
                color: '#FFDA59',
                duration: 1.4,
                stagger: 0.05
            });
        }

    /////////////////////////////////////////////////////

    //return img gsap
    gsap.registerPlugin(ScrollTrigger);

    let revealContainers = document.querySelectorAll(".return");

    revealContainers.forEach((container) => {
    let image = container.querySelector("img");
    let tl = gsap.timeline({
        scrollTrigger: {
        trigger: container,
        toggleActions: "restart none none reset"
        }
    });

    tl.set(container, { autoAlpha: 1 });
    tl.from(container, 1.5, {
        xPercent: -100,
        ease: Power2.out
    });
    tl.from(image, 1.5, {
        xPercent: 100,
        scale: 1.3,
        delay: -1.5,
        ease: Power2.out
    });
    });

    //GSAP smooth animation
    gsap.registerPlugin(ScrollTrigger, ScrollSmoother, ScrollToPlugin);

    if ($('#smooth-wrapper').length && $('#smooth-content').length) {
  
       gsap.config({
          nullTargetWarn: false,
       });
  
       let smoother = ScrollSmoother.create({
          smooth: 2,
          effects: true,
          smoothTouch: false,
          normalizeScroll: false,
          ignoreMobileResize: true,
       });
    }

    //GSAP title animation
    if ($('.rr_title_anim').length > 0) {
        let splitTitleLines = gsap.utils.toArray(".rr_title_anim");
        splitTitleLines.forEach(splitTextLine => {
           const tl = gsap.timeline({
              scrollTrigger: {
                 trigger: splitTextLine,
                 start: 'top 90%',
                 end: 'bottom 60%',
                 scrub: false,
                 markers: false,
                 toggleActions: 'play none none reverse'
              }
           });
    
           const itemSplitted = new SplitText(splitTextLine, { type: "words, lines" });
           gsap.set(splitTextLine, { perspective: 400 });
           itemSplitted.split({ type: "lines" })
           tl.from(itemSplitted.lines, {
              duration: 1,
              delay: 0.3,
              opacity: 0,
              rotationX: -80,
              force3D: true,
              transformOrigin: "top center -50",
              stagger: 0.1
           });
        });
     }

     //split-text animation
     let heroes = document.querySelectorAll(".hero");
     
     heroes.forEach(hero => {
       let split = new SplitText(hero.querySelector("._split_text"), { type: "chars, words" }),
           tl = gsap.timeline({
           scrollTrigger: {
             trigger: hero,
             start: "top bottom",
             toggleActions: "play none none reverse",
                 onEnter: () => {
           tl.timeScale(2.3);
         },
         
         onLeaveBack: () => {
           tl.timeScale(2.3).reverse();
         },
           }
         });
       tl.to(hero.querySelector(".sup_hero"), { opacity: 1, x: -50, ease: "back" })
         .from(split.chars, {
           opacity: 0,
           y: 50,
           rotation: 1,
           duration: 2,
           ease: "back",
           stagger: 0.05
         });
     });
    //split-text animation end

    //fade-top gsap animation
    if ($(".fade-wrapper").length > 0) {
        $(".fade-wrapper").each(function () {
            var section = $(this);
            var fadeItems = section.find(".fade-top");
    
            fadeItems.each(function (index, element) {
            var delay = index * 0.15;
    
            gsap.set(element, {
                opacity: 0,
                y: 100,
            });
    
            ScrollTrigger.create({
                trigger: element,
                start: "top 100%",
                end: "bottom 60%",
                toggleActions: "play none none reverse",
                scrub: 0.5,
                onEnter: function () {
                gsap.to(element, {
                    opacity: 1,
                    y: 0,
                    duration: 1,
                    delay: delay,
                });
                },
                once: true,
            });
            });
        });
    }

    //GSAP END
    
    /*======================================
   Data Css js
   ========================================*/
    $("[data-background]").each(function() {
        $(this).css(
            "background-image",
            "url( " + $(this).attr("data-background") + "  )"
        );
    });

    $("[data-width]").each(function() {
        $(this).css("width", $(this).attr("data-width"));
    });

    $("[data-bg-color]").each(function() {
        $(this).css("background-color", $(this).attr("data-bg-color"));
    });

  /*======================================
	Mobile Menu Js
	========================================*/
  $("#mobile-menu").meanmenu({
    meanMenuContainer: ".mobile-menu",
    meanScreenWidth: "1199",
    meanExpand: ['<i class="fa-regular fa-angle-right"></i>'],
  });

  /*======================================
	Sidebar Toggle
	========================================*/
  $(".offcanvas__close,.offcanvas__overlay").on("click", function () {
    $(".offcanvas__area").removeClass("info-open");
    $(".offcanvas__overlay").removeClass("overlay-open");
  });
  // Scroll to bottom then close navbar
  $(window).scroll(function(){
    if($("body").scrollTop() > 0 || $("html").scrollTop() > 0) {
        $(".offcanvas__area").removeClass("info-open");
        $(".offcanvas__overlay").removeClass("overlay-open");
    }
  });
  $(".sidebar__toggle").on("click", function () {
    $(".offcanvas__area").addClass("info-open");
    $(".offcanvas__overlay").addClass("overlay-open");
  });

  /*======================================
	Body overlay Js
	========================================*/
  $(".body-overlay").on("click", function () {
    $(".offcanvas__area").removeClass("opened");
    $(".body-overlay").removeClass("opened");
  });

  /*======================================
	Sticky Header Js
	========================================*/

  $(window).scroll(function () {
    if ($(this).scrollTop() > 250) {
      $("#header-sticky").addClass("rs-sticky");
    } else {
      $("#header-sticky").removeClass("rs-sticky");
    }
  });

    /*** pricing table */
    const pricingMonthlyBtn = $("#monthly-btn"),
        pricingYearlyBtn = $("#yearly-btn"),
        pricingValues = $(".pricing-card-price h2");

    if (pricingMonthlyBtn[0] && pricingYearlyBtn[0] && pricingValues.length > 0) {
        pricingMonthlyBtn[0].addEventListener("click", function () {
            updatePricingValues("monthly");
            pricingYearlyBtn[0].classList.remove("active");
            pricingMonthlyBtn[0].classList.add("active");
        });

        pricingYearlyBtn[0].addEventListener("click", function () {
            updatePricingValues("yearly");
            pricingMonthlyBtn[0].classList.remove("active");
            pricingYearlyBtn[0].classList.add("active");
        });
    }

    function updatePricingValues(option) {
        pricingValues.each(function () {
            const pricingValue = $(this);
            const yearlyValue = pricingValue.attr("data-yearly");
            const monthlyValue = pricingValue.attr("data-monthly");

            const newValue = option === "monthly" ? monthlyValue : yearlyValue;
            pricingValue.html(newValue);
        });
    }

  /*======================================
	MagnificPopup image view
	========================================*/
  $(".popup-image").magnificPopup({
    type: "image",
    gallery: {
      enabled: true,
    },
  });

  /*======================================
	MagnificPopup video view
	========================================*/
  $(".popup-video").magnificPopup({
    type: "iframe",
  });


  /*======================================
	Wow Js
	========================================*/
    if ($('.wow').length) {
        var wow = new WOW({
            boxClass: 'wow', // animated element css class (default is wow)
            animateClass: 'animated', // animation css class (default is animated)
            offset: 0, // distance to the element when triggering the animation (default is 0)
            mobile: false, // trigger animations on mobile devices (default is true)
            live: true // act on asynchronously loaded content (default is true)
        });
        wow.init();
    }

  /*======================================
	Button scroll up js
	========================================*/
    
    /*======================================
	One Page Scroll Js
	========================================*/
    /*** Scroll Nav */
    var link = $('.mean-nav ul li a');

    link.on('click', function(e) {
        var target = $($(this).attr('href'));
        $('html, body').animate({
            scrollTop: target.offset().top - 76
        }, 600);
        $(this).parent().addClass('active');
        e.preventDefault();
    });

    $(window).on('scroll', function(){
        scrNav();
    });

    function scrNav() {
        var sTop = $(window).scrollTop();
        $('section').each(function() {
            var id = $(this).attr('id'),
                offset = $(this).offset().top-1,
                height = $(this).height();
            if(sTop >= offset && sTop < offset + height) {
                link.parent().removeClass('active');
                $('.main-menu').find('[href="#' + id + '"]').parent().addClass('active');
            }
        });
    }
    scrNav();

    /*======================================
	Smoth animatio Js
	========================================*/
    $(document).on('click', '.smoth-animation', function (event) {
        event.preventDefault();
        $('html, body').animate({
            scrollTop: $($.attr(this, 'href')).offset().top - 50
        }, 300);
    });

  /*======================================
    All Swiper Slide
  ========================================*/

    // seken testimonial__carousel
    var swiperProject = new Swiper(".testimonial__carousel", {
        slidesPerView: 4,
        spaceBetween: 20,
        loop: true,
        slidesPerGroupSkip: 1,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        breakpoints: {
            320: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            767: {
                slidesPerView: 2,
                spaceBetween: 20,
            },
            1200: {
                slidesPerView: 4,
            },
        },
    });
    // hero-10-slide js  --------
    var swiper = new Swiper(".hero-10-slide-active", {
        slidesPerView: 5.5,
        spaceBetween: 30,
        loop: true,
        slidesPerGroupSkip: 0,
        centeredSlides: true,
        autoplay: true,
        centerMode: false,
        breakpoints: {
            1200: {
                slidesPerView: 4.5,
                spaceBetween: 30,
            },
            992: {
                sliderPerView: 4,
                spaceBetween: 30,
            },
            768: {
                slidesPerView: 3,

            },
            576: {
                slidesPerView: 2,
                spaceBetween: 30,
            },
            360: {
                slidesPerView: 1,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });
    // seken testimonial-6__carousel
    var swiperProject = new Swiper(".testimonial-6__carousel", {
        slidesPerView: 4,
        spaceBetween: 20,
        loop: true,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        navigation: {
            prevEl: ".testimonial-6__slider-arrow-prev",
            nextEl: ".testimonial-6__slider-arrow-next",
        },
        breakpoints: {
            320: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            767: {
                slidesPerView: 2,
                spaceBetween: 20,
            },
            1200: {
                slidesPerView: 4,
            },
        },
    });

    //  brands-10 js start ----------
    var swiper = new Swiper(".brands-10-active", {
        slidesPerView: 'auto',
        spaceBetween: 80,
        freemode: true,
        centeredSlides: true,
        loop: true,
        speed: 4000,
        allowTachMode: false,
        autoplay: {
            delay: 1,
            disableOnInteraction: true,
        },
        breakpoints: {
            1200: {
                slidesPerView: 6,
                spaceBetween: 30,
            },
            992: {
                sliderPerView: 5,
                spaceBetween: 30,
            },
            768: {
                slidesPerView: 3,
                spaceBetween: 20,
            },
            576: {
                slidesPerView: 3,
                spaceBetween: 30,
            },
            360: {
                slidesPerView: 2,
                spaceBetween: 30,
            },
            0: {
                slidesPerView: 2,
                spaceBetween: 30,
            },
        },
    });

    // support-10 slide js ----------
    var swiper = new Swiper(".support-slider-actives", {
        slidesPerView: 'auto',
        spaceBetween: 10,
        freemode: true,
        centeredSlides: true,
        loop: true,
        speed: 4000,
        allowTachMode: false,
        autoplay: {
            delay: 1,
            disableOnInteraction: true,
        },
        breakpoints: {
            1200: {
                slidesPerView: 4,
            },
            992: {
                sliderPerView: 3,
                spaceBetween: 10,
            },
            768: {
                slidesPerView: 3,
                spaceBetween: 10,
            },
            576: {
                slidesPerView: 3,
                spaceBetween: 10,
            },
            360: {
                slidesPerView: 2,
                spaceBetween: 10,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    // testimonial-10 js  ----------
    var swiper = new Swiper(".testimonial-10-active", {
        slidesPerView: 1,
        spaceBetween: 0,
        loop: true,
        slidesPerGroupSkip: 1,
        centeredSlides: true,
        // autoplay: true,
        centerMode: true,
        keyboard: {
          enabled: true,
        },
        pagination: {
          el: ".swiper-pagination",
          clickable: true,
        },
        navigation: {
          nextEl: ".testimonial-10__swiper-button-next",
          prevEl: ".testimonial-10__swiper-button-prev",
        },
    });

    // seken testimonial-4__carousel
    var swiperProject = new Swiper(".testimonial-4__slider", {
        slidesPerView: 1,
        spaceBetween: 50,
        loop: true,
        slidesPerGroupSkip: 3,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        navigation: {
            prevEl: ".testimonial-4__slider-arrow-prev",
            nextEl: ".testimonial-4__slider-arrow-next",
        },
    });
    // blog-list__slider
    var swiperProject = new Swiper(".blog-list__slider", {
        slidesPerView: 1,
        // spaceBetween: 50,
        loop: true,
        // slidesPerGroupSkip: 3,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        // scrollbar: {
        //     el: ".swiper-scrollbar",
        //     hide: false,
        //     draggable: true,
        // },
        navigation: {
            prevEl: ".testimonial-4__slider-arrow-prev",
            nextEl: ".testimonial-4__slider-arrow-next",
        },
    });


    // seken Show more review button
    $(document).ready(function() {
        let itemsToShow = 3; 
        let itemsIncrement = 3;
        let totalItems = $('.content').length;
      
        $('.content').slice(itemsToShow).hide();
      
        $('.loadmore').on('click', function() {
          let hiddenItems = $('.content:hidden'); 
          hiddenItems.slice(0, itemsIncrement).fadeIn(); 
      
          if (hiddenItems.length <= itemsIncrement) {
            $('.loadmore').fadeOut();
          }

          $('.testimonial-2__area').addClass('hide_overlay');
        });
      });
    // seken Show more review button end

      //seken rr__latest-blog H3
      var swiper = new Swiper(".rr__latest-blog", {
        slidesPerView: 3,
        autoplay: true,
        speed: 600,
        spaceBetween: 30,
        loop: true,
        keyboard: {
          enabled: true,
        },
        pagination: {
          el: ".swiper-pagination",
          clickable: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
      });
      //seken review-9__slider H9
      var swiper = new Swiper(".review-9__slider", {
        slidesPerView: 3,
        autoplay: true,
        speed: 600,
        spaceBetween: 30,
        loop: true,
        keyboard: {
          enabled: true,
        },
        pagination: {
          el: ".swiper-pagination",
          clickable: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
      });

      //seken blog-4-slider H4
      var swiper = new Swiper(".blog-4-slider", {
        slidesPerView: 3,
        autoplay: true,
        speed: 600,
        spaceBetween: 30,
        loop: true,
        keyboard: {
          enabled: true,
        },
        pagination: {
          el: ".swiper-pagination-4",
          clickable: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
      });

      //seken testi-slider H3
      var testimonials = new Swiper(".testi-slider", {
        slidesPerView: 1,
        slidesPerGroup: 1,
        spaceBetween: 0,
        loop: true,
        autoplay: true,
        speed: 600,
        navigation: {
            nextEl: ".testi-next",
            prevEl: ".testi-prev",
        }, 
    });

    //seken rrseken__fast-content H5
    var swiper = new Swiper(".rrseken__fast-content", {
        slidesPerView: 4,
        spaceBetween: 30,
        loop: true,
        navigation: {
            nextEl: ".rrseken-swiper-button-next",
            prevEl: ".rrseken-swiper-button-prev",
          },
        breakpoints: {
            1301: {
                slidesPerView: 4,
            },
            992: {
                slidesPerView: 3,
            },
            600: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    //seken testimonial-5__slide H5
    var swiper = new Swiper(".testimonial-5__slide", {
        slidesPerView: 2,
        spaceBetween: 30,
        loop: true,
        navigation: {
            nextEl: ".rrseken-swiper-button-next",
            prevEl: ".rrseken-swiper-button-prev",
          },
        breakpoints: {
            1301: {
                slidesPerView: 2,
            },
            992: {
                slidesPerView: 2,
            },
            600: {
                slidesPerView: 1,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    //seken blog-5__slider H5
    var swiper = new Swiper(".blog-5__slider", {
        slidesPerView: 3,
        spaceBetween: 30,
        loop: true,
        navigation: {
            nextEl: ".blog-5-next",
            prevEl: ".blog-5-prev",
          },
          breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    $('.grid').isotope({
        itemSelector: '.grid-item',
        percentPosition: true,
        masonry: {
          columnWidth: 1
          
        }
    })

    //seken aifunction-slide H2
    var swiper = new Swiper(".aifunction-slide", {
    slidesPerView: 4,
    spaceBetween: 30,
    loop: true,
    navigation: {
        prevEl: ".aifunction-slide-button-prev",
        nextEl: ".aifunction-slide-button-next",
    },
    pagination: {
        el: ".swiper-pagination",
        clickable: true,
    },
    breakpoints: {
        1201: {
            slidesPerView: 4,
        },
        716: {
            slidesPerView: 2,
        },
        0: {
            slidesPerView: 1,
        },
    },
    });

    //seken related-products-slide shop-details
    var swiper = new Swiper(".related-products", {
    slidesPerView: 4,
    spaceBetween: 30,
    loop: true,
    autoplay: true,
    speed: 1000,
    breakpoints: {
        1201: {
            slidesPerView: 4,
        },
        716: {
            slidesPerView: 2,
        },
        0: {
            slidesPerView: 1,
        },
    },
    });
    // SEKEN blog__slider-6
    var swiper = new Swiper(".latest-trends__item", {
        slidesPerView: 3,
        loop: true,
        autoplay: true,
        centeredSlides: false,
        spaceBetween: 30,
        slidesPerGroupSkip: 1,
        grabCursor: true,
        keyboard: {
          enabled: true,
        },
        breakpoints: {
          1850: {
            slidesPerView: 3,
            slidesPerGroup: 1,
          },

          1230: {
            slidesPerView: 2,
            slidesPerGroup: 1,
          },

          768: {
            slidesPerView: 1.5,
            slidesPerGroup: 1,
          },
          0: {
            slidesPerView: 1,
            slidesPerGroup: 1,
          },
        },
        scrollbar: {
          el: ".swiper-scrollbar-drag",
        },
      });
    //seken hero-4-slider H4
    var swiper = new Swiper(".hero-4-slider", {
    slidesPerView: 6,
    spaceBetween: 30,
    loop: true,
    centeredSlides: true,
    freemode: true,
    speed:4000,
    allowTouchMove: false,
        autoplay:{
        delay: 1,
        disableOnInteraction: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 6,
            },
            1024: {
                slidesPerView: 4,
            },
            // 740: {
            //     slidesPerView: 3,
            // },
            575: {
                slidesPerView: 3,
            },
            370: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    //Swiper Slider For Shop
    var swiper = new Swiper(".product-gallary-thumb", {
        spaceBetween: 10,
        slidesPerView: 5,
        freeMode: true,
        watchSlidesProgress: true,
        direction: 'vertical',
    });
    
    var swiper2 = new Swiper(".product-gallary", {
        spaceBetween: 10,
        loop: true,
        navigation: {
            nextEl: ".swiper-nav-next",
            prevEl: ".swiper-nav-prev",
        },
        thumbs: {
            swiper: swiper,
        },
    });
    var audio = new Audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3");

    $('.audio').on("click",function(){
    if($(this).hasClass('fa-play'))
    {
        $(this).removeClass('fa-play');
        $(this).addClass('fa-pause');
        audio.play();
    }
    else
    {
        $(this).removeClass('fa-pause');
        $(this).addClass('fa-play');
        audio.pause();
    }
    });

    audio.onended = function() {
        $("#play-pause-button").removeClass('fa-pause');
        $("#play-pause-button").addClass('fa-play');
    };
    //count
    function handleQuantityButtons() {
        $('.count-wrap .minus').click(function() {
            var input = $(this).closest('.count-wrap').find('input.qty');
            var currentValue = parseInt(input.val());
            if (currentValue > 1) {
                input.val(currentValue - 1).change();
            }
        });

        $('.count-wrap .plus').click(function() {
            var input = $(this).closest('.count-wrap').find('input.qty');
            var currentValue = parseInt(input.val());
            input.val(currentValue + 1).change();
        });
    }
    // Easy Pie Chart
    const piechart = document.querySelectorAll(".piechart");
    piechart.forEach(function (el) {
        const waypoint = new Waypoint({
            element: el,
            handler: function () {
                const easyPieChart = new EasyPieChart(el, {
                    scaleColor: "transparent",
                    lineWidth: 10,
                    lineCap: "round",
                    trackColor: " rgba(255, 255, 255, 0.3)",
                    barColor: "#fff",
                    size: 150,
                    rotate: 0,
                    animate: 1000,
                    onStep: function (value) {
                        this.el.querySelector("span").textContent = Math.round(value);
                    },
                    onStop: function (value, to) {
                        this.el.querySelector("span").textContent = Math.round(to);
                    },
                });
                this.destroy();
            },
            offset: "80%",
            triggerOnce: true,
        });
    });

      // Project Style3
    if ($(".slider_hover__item li").length) {
        $(".slider_hover__item li").each(function () {
            let self = $(this);

            self.on("mouseenter", function () {
                console.log($(this));
                $(".slider_hover__item li").removeClass("active");
                $(this).addClass("active");
            });
        });
    }

      $('.col-custom').on("click", function () {
		$('#features-item-thumb').removeClass().addClass($(this).attr('rel'));
		$(this).addClass('active').siblings().removeClass('active');
	});

    // Popup Search Box
    $(function () {
        $("#popup-search-box").removeClass("toggled");

        $(".dl-search-icon").on("click", function (e) {
            e.stopPropagation();
            $("#popup-search-box").toggleClass("toggled");
            $("#popup-search").focus();
        });

        $("#popup-search-box input").on("click", function (e) {
            e.stopPropagation();
        });

        $("#popup-search-box, body").on("click", function () {
            $("#popup-search-box").removeClass("toggled");
        });
    });

    // $('.lan-select select, .nice-select-select select').niceSelect();
    $('.take-appointment-3__form-input-select select, .lan-select select, .nice-select-select select').niceSelect();
    $( "#datepicker" ).datepicker({
        dateFormat: "mm/dd/yy" 
    });

    $('#getting-started').countdown('2025/01/01', function(event) {
        $(this).html(event.strftime(' <div><span>%D</span></div>  <div><span>%H</span></div> <div><span>%M</span></div> <div><span>%S</span></div>'));
      });


      /*** lastNobullet */
    function lastNobullet() {
        var lastElement = false;
        $(".footer__copyright-menu ul li, .last_item_not_horizental_bar .col-lg-4").each(function() {
            if (lastElement && lastElement.offset().top != $(this).offset().top) {
                $(lastElement).addClass("no_bullet");
            } else {
                $(lastElement).removeClass("no_bullet");
            }
            lastElement = $(this);
        }).last().addClass("no_bullet");
    };
    lastNobullet();

    $(window).resize(function(){
        lastNobullet();
    });

    $('#contact__form').submit(function(event) {
        event.preventDefault();
        var form = $(this);
        $('.loading-form').show();

        setTimeout(function() { 
            $.ajax({
            type: form.attr('method'),
            url: form.attr('action'),
            data: form.serialize()
            }).done(function(data) {
                $('.loading-form').hide();
                $('.contact__form').append('<p class="success-message mt-3 mb-0">Your message has been sent successfully.</p>');
            }).fail(function(data) {
                $('.loading-form').hide();
                $('.contact__form').append('<p class="error-message mt-3 mb-0">Something went wrong. Please try again later.</p>');

            });
        }, 1000);
      });

    $('#showlogin').on('click', function () {
        $('#checkout-login').slideToggle(400);
    });
    $('#showcoupon').on('click', function () {
        $('#checkout_coupon').slideToggle(400);
    });
    

    // Custom Cursor
    $("body").append('<div class="mt-cursor"></div>');
    var cursor = $(".mt-cursor"),
        linksCursor = $("a, .swiper-nav, button, .cursor-effect"),
        crossCursor = $(".cross-cursor");

    $(window).on("mousemove", function (e) {
        cursor.css({
            transform: "translate(" + (e.clientX - 15) + "px," + (e.clientY - 15) + "px)",
            visibility: "inherit",
        });
    });

    // Page Scroll Percentage
    function scrollTopPercentage() {
        const scrollPercentage = () => {
            const scrollTopPos = document.documentElement.scrollTop;
            const calcHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const scrollValue = Math.round((scrollTopPos / calcHeight) * 100);
            const scrollElementWrap = $("#scroll-percentage");

            scrollElementWrap.css("background", `conic-gradient( var(--rr-theme-primary2) ${scrollValue}%, var(--rr-common-white) ${scrollValue}%)`);
            
            // ScrollProgress
            if ( scrollTopPos > 100 ) {
                scrollElementWrap.addClass("active");
            } else {
                scrollElementWrap.removeClass("active");
            }

            if( scrollValue < 96 ) {
                $("#scroll-percentage-value").text(`${scrollValue}%`);
            } else {
                $("#scroll-percentage-value").html('<i class="fa-sharp fa-regular fa-arrow-up-long"></i>');
            }
        }
        window.onscroll = scrollPercentage;
        window.onload = scrollPercentage;

        // Back to Top
        function scrollToTop() {
            document.documentElement.scrollTo({
                top: 0,
                behavior: "smooth"
            });
        }
        
        $("#scroll-percentage").on("click", scrollToTop);
    }

    scrollTopPercentage();

    // slider js -----------
    $(document).ready(function () {
        function sliderAnimations(elements) {
            var animationEndEvents = "webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend";
            elements.each(function () {
                var $this = $(this);
                var $animationDelay = $this.data("delay");
                var $animationDuration = $this.data("duration");
                var $animationType = "pixfix-animation " + $this.data("animation");
                $this.css({
                    "animation-delay": $animationDelay,
                    "-webkit-animation-delay": $animationDelay,
                    "animation-duration": $animationDuration,
                });
                $this.addClass($animationType).one(animationEndEvents, function () {
                    $this.removeClass($animationType);
                });
            });
        }
        var sliderOptions = {
            speed: 1500,
            autoplay: {
                delay: 7000,
            },
            disableOnInteraction: false,
            initialSlide: 0,
            parallax: false,
            mousewheel: false,
            loop: true,
            grabCursor: true,
            navigation: {
                nextEl: ".slider-arrow .slider-next",
                prevEl: ".slider-arrow .slider-prev",
            }
        };
        sliderOptions.on = {
            slideChangeTransitionStart: function () {
                var swiper = this;
                var animatingElements = $(swiper.slides[swiper.activeIndex]).find("[data-animation]");
                sliderAnimations(animatingElements);
            },

            resize: function () {
                this.update();
            },
        };

        var swiper = new Swiper(".banner-4__active", sliderOptions);
    });
    
    // Progress Item 7
    document.addEventListener("DOMContentLoaded", () => {
        const progressItems = document.querySelectorAll(".progress-7__item");
        const progressBox = document.querySelector(".progress-7__box");

        if(progressItems && progressBox){
            // Define colors for each step
        const colors = ["#36F165"];

        window.addEventListener("scroll", () => {
            let activeIndex = -1;

            progressItems.forEach((item, index) => {
                const rect = item.getBoundingClientRect();
                const isInView = rect.top < window.innerHeight / 2 && rect.bottom > 0;

                if (isInView) {
                    item.classList.add("active");
                    activeIndex = index;
                } else {
                    item.classList.remove("active");
                }
            });

            if (activeIndex >= 0) {
                const activeItem = progressItems[activeIndex];
                const boxRect = progressBox.getBoundingClientRect();
                const itemRect = activeItem.getBoundingClientRect();

                // Calculate the height for the progress line
                const newHeight = itemRect.top + itemRect.height / 1 - boxRect.top;

                // Update the progress line height and color
                progressBox.style.setProperty("--line-height", `${newHeight}px`);
                progressBox.style.setProperty("--line-color", colors[activeIndex] || "#36F165");
            } else {
                // Reset the line height when no item is active
                progressBox.style.setProperty("--line-height", `0px`);
            }
        });
        }
    });

    // Register GSAP plugins
    var device_width = window.screen.width;

    // Pin Active
    var pin_fixed = document.querySelector('.pin-element');
    if (pin_fixed && device_width > 1199) {

        gsap.to(".pin-element", {
            scrollTrigger: {
                trigger: ".pin-area",
                pin: ".pin-element",
                start: "top top",
                end: "bottom 60%",
                pinSpacing: false,
            }
        });
    }

    var pin_fixed = document.querySelector('.pin-element_2');
    if (pin_fixed && device_width > 1199) {

        gsap.to(".pin-element_2", {
            scrollTrigger: {
                trigger: ".pin-area-2",
                pin: ".pin-element_2",
                start: "top top",
                end: "bottom botttom",
                pinSpacing: false,
            }
        });
    }
    // seken testimonial-8__carousel
    var swiperProject1 = new Swiper(".testimonial-8__slider", {
        slidesPerView: 2,
        spaceBetween: 30,
        loop: true,
        slidesPerGroupSkip: 3,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        pagination: {
            el: ".swiper-pagination-8",
            clickable: true,
        },
        breakpoints: {
            320: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            767: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            1200: {
                slidesPerView: 2,
            },
        },
    });
    //seken blog-8__slider H5
    var swiper = new Swiper(".blog-8__slider", {
        slidesPerView: 3,
        spaceBetween: 30,
        loop: true,
        autoplay: true,
        speed: 600,
        navigation: {
            nextEl: ".blog-8__button__next",
            prevEl: ".blog-8__button__prev",
        },
        breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });
    var lates_update__item = document.querySelectorAll(".lates-update__item");
    var counter = 0

    if (device_width > 1199) {
        lates_update__item.forEach((gallery) => {
            gsap.to(gallery, {
                scrollTrigger: {
                    trigger: gallery,
                    pin: gallery,
                    pinSpacing: false,
                    start: "top 80px",
                    delay: 1,
                },
            });
        });
    }

    var swiper1 = new Swiper(".about-us-7__slider-1", {
        direction: "vertical",
        slidesPerView: "auto",
        spaceBetween: 10,
        speed: 7e3,
        loop: !0,
        freemode: true,
        autoplay: {
            delay: 0.9,
            disableOnInteraction: !1
        }
    }),
        swiper4 = new Swiper(".about-us-7__slider-2", {
            direction: "vertical",
            spaceBetween: 10,
            speed: 8e3,
            loop: !0,
            slidesPerView: "auto",
            freemode: true,
            autoplay: {
                delay: 0.9,
                disableOnInteraction: !1
            }
        }),
        swiper3 = new Swiper(".about-us-7__slider-3", {
            direction: "vertical",
            spaceBetween: 10,
            speed: 13e3,
            loop: !0,
            slidesPerView: "auto",
            freemode: true,
            autoplay: {
                delay: 0.9,
                disableOnInteraction: !1
            }
        });

    //seken brand-7__silder H7
    var swiper = new Swiper(".brand-7__silder", {
        slidesPerView: 6,
        spaceBetween: 30,
        loop: true,
        centeredSlides: true,
        freemode: true,
        speed: 4000,
        allowTouchMove: false,
        autoplay: {
            delay: 1,
            disableOnInteraction: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 6,
            },
            1024: {
                slidesPerView: 4,
            },
            575: {
                slidesPerView: 3,
            },
            370: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 2,
            },
        },
    });
    //seken secure-refined-silder H7
    var swiper = new Swiper(".secure-refined-silder", {
        slidesPerView: 4,
        spaceBetween: 30,
        loop: true,
        centeredSlides: true,
        freemode: true,
        speed: 4000,
        allowTouchMove: false,
        autoplay: {
            delay: 1,
            disableOnInteraction: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 4,
            },
            1024: {
                slidesPerView: 4,
            },
            575: {
                slidesPerView: 3,
            },
            370: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 2,
            },
        },
    });

    // seken testimonial-7__silder
    var testimonial = new Swiper(".testimonial-7__silder", {
        slidesPerView: 4,
        spaceBetween: 20,
        loop: true,
        slidesPerGroupSkip: 1,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        navigation: {
            prevEl: ".testimonial-7__slider-arrow-prev",
            nextEl: ".testimonial-7__slider-arrow-next",
        },
        breakpoints: {
            320: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            767: {
                slidesPerView: 2,
                spaceBetween: 20,
            },
            1200: {
                slidesPerView: 4,
            },
        },
    });

    //design-services-7__silder
    var design_services = new Swiper(".design-services-7__silder", {
        slidesPerView: 1,
        spaceBetween: 0,
        loop: true,
        slidesPerGroupSkip: 1,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        navigation: {
            prevEl: ".design-services-7__slider-arrow-prev",
            nextEl: ".design-services-7__slider-arrow-next",
        },
    });


})(jQuery);
/*
 * Make sure that the anonymous function will create a scope so that code
 * completion can happen for its arguments
 */
setTimeout(function(one, two, delay) {
    assertEquals(one, 1111);
    assertEquals(two, 2222);
    assertTrue(delay > 0);
}, 0, 1111, 2222);
